"""Verify clarification state without calling a language model."""

import pytest

from customer_segmentation_assistant.conversation import SegmentConversation


def test_follow_up_preserves_known_contract():
    conversation = SegmentConversation()

    first = conversation.update({
        "contract": "One year",
        "minimum_churn_probability": None,
    })
    assert first == {
        "kind": "clarification",
        "question": "Which minimum churn probability should I use?",
    }

    second = conversation.update({
        "contract": None,
        "minimum_churn_probability": 0.7,
    })
    assert second == {
        "kind": "tool_call",
        "tool": "summarize_segment",
        "arguments": {
            "contract": "One year",
            "minimum_churn_probability": 0.7,
        },
    }


def test_follow_up_preserves_zero_threshold():
    conversation = SegmentConversation()

    conversation.update({
        "contract": None,
        "minimum_churn_probability": 0.0,
    })
    result = conversation.update({
        "contract": "Month-to-month",
        "minimum_churn_probability": None,
    })

    assert result["kind"] == "tool_call"
    assert result["arguments"]["minimum_churn_probability"] == 0.0


def test_missing_values_do_not_erase_known_criteria():
    conversation = SegmentConversation()
    conversation.update({
        "contract": "Two year",
        "minimum_churn_probability": None,
    })

    result = conversation.update({
        "contract": None,
        "minimum_churn_probability": None,
    })

    assert conversation.criteria["contract"] == "Two year"
    assert result["question"] == "Which minimum churn probability should I use?"


def test_explicit_new_value_replaces_previous_value():
    conversation = SegmentConversation()
    conversation.update({
        "contract": "One year",
        "minimum_churn_probability": 0.7,
    })

    result = conversation.update({
        "contract": None,
        "minimum_churn_probability": 0.8,
    })

    assert result["arguments"] == {
        "contract": "One year",
        "minimum_churn_probability": 0.8,
    }


def test_invalid_update_preserves_previous_state():
    conversation = SegmentConversation()
    conversation.update({
        "contract": "One year",
        "minimum_churn_probability": None,
    })
    previous = dict(conversation.criteria)

    with pytest.raises(ValueError):
        conversation.update({
            "contract": "Two year",
            "minimum_churn_probability": 70,
        })

    assert conversation.criteria == previous


def test_conversations_have_separate_state():
    first = SegmentConversation()
    second = SegmentConversation()

    first.update({
        "contract": "One year",
        "minimum_churn_probability": None,
    })

    assert second.criteria == {
        "contract": None,
        "minimum_churn_probability": None,
    }