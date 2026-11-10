"""Verify comparison state without model calls."""

import pytest

from customer_segmentation_assistant import comparison_request
from customer_segmentation_assistant.comparison_conversation import (
    ComparisonConversation,
)


def test_follow_up_preserves_contracts():
    conversation = ComparisonConversation()

    first = conversation.update({
        "contracts": ["Month-to-month", "One year"],
        "minimum_churn_probability": None,
    })
    assert first["kind"] == "clarification"

    second = conversation.update({
        "contracts": [],
        "minimum_churn_probability": 0.7,
    })

    assert second == {
        "kind": "comparison",
        "arguments": {
            "contracts": ["Month-to-month", "One year"],
            "minimum_churn_probability": 0.7,
        },
    }


def test_zero_threshold_is_preserved():
    conversation = ComparisonConversation()
    conversation.update({
        "contracts": [],
        "minimum_churn_probability": 0.0,
    })

    result = conversation.update({
        "contracts": ["One year", "Two year"],
        "minimum_churn_probability": None,
    })

    assert result["arguments"]["minimum_churn_probability"] == 0.0


def test_new_contract_selection_replaces_old_selection():
    conversation = ComparisonConversation()
    conversation.update({
        "contracts": ["Month-to-month", "One year"],
        "minimum_churn_probability": 0.7,
    })

    result = conversation.update({
        "contracts": ["One year", "Two year"],
        "minimum_churn_probability": None,
    })

    assert result["arguments"]["contracts"] == ["One year", "Two year"]
    assert result["arguments"]["minimum_churn_probability"] == 0.7


def test_invalid_update_preserves_state():
    conversation = ComparisonConversation()
    conversation.update({
        "contracts": ["One year", "Two year"],
        "minimum_churn_probability": None,
    })

    with pytest.raises(ValueError):
        conversation.update({
            "contracts": ["Other"],
            "minimum_churn_probability": 0.7,
        })

    assert conversation.criteria == {
        "contracts": ["One year", "Two year"],
        "minimum_churn_probability": None,
    }


def test_conversations_and_returned_lists_are_independent():
    first = ComparisonConversation()
    second = ComparisonConversation()
    supplied = {
        "contracts": ["One year", "Two year"],
        "minimum_churn_probability": 0.7,
    }

    result = first.update(supplied)
    supplied["contracts"].clear()
    result["arguments"]["contracts"].clear()

    assert first.criteria["contracts"] == ["One year", "Two year"]
    assert second.criteria == {
        "contracts": [],
        "minimum_churn_probability": None,
    }


def test_threshold_follow_up_ignores_spurious_contract(monkeypatch):
    conversation = ComparisonConversation()
    conversation.update({
        "contracts": ["Month-to-month", "One year"],
        "minimum_churn_probability": None,
    })

    def fake_extraction(question, *, model):
        return {
            "contract": "One year",
            "minimum_churn_probability": 0.7,
        }

    monkeypatch.setattr(
        comparison_request,
        "extract_segment_criteria",
        fake_extraction,
    )
    monkeypatch.setattr(
        comparison_request,
        "check_comparison_scope",
        lambda question, *, model: [],
    )

    extracted = comparison_request.extract_comparison_follow_up(
        "Use a minimum churn probability of 70%.",
        current_criteria=conversation.criteria,
    )
    result = conversation.update(extracted)

    assert result == {
        "kind": "comparison",
        "arguments": {
            "contracts": ["Month-to-month", "One year"],
            "minimum_churn_probability": 0.7,
        },
    }


def test_unsupported_follow_up_blocks_conversation_until_reset():
    conversation = ComparisonConversation()
    conversation.update({
        "contracts": ["Month-to-month", "One year"],
        "minimum_churn_probability": None,
    })

    unsupported = {
        "kind": "unsupported",
        "message": "Tenure filters are not supported. Start a new comparison.",
    }
    assert conversation.update(unsupported) == unsupported

    result = conversation.update({
        "contracts": [],
        "minimum_churn_probability": 0.7,
    })

    assert result == unsupported
    assert conversation.criteria["minimum_churn_probability"] is None

    fresh = ComparisonConversation()
    assert fresh.unsupported_message is None


def test_unsupported_follow_up_skips_criteria_extraction(monkeypatch):
    monkeypatch.setattr(
        comparison_request,
        "check_comparison_scope",
        lambda question, *, model: ["tenure of at least 24 months"],
    )

    def unexpected_extraction(*args, **kwargs):
        raise AssertionError("Criteria extraction must not run.")

    monkeypatch.setattr(
        comparison_request,
        "extract_segment_criteria",
        unexpected_extraction,
    )

    result = comparison_request.extract_comparison_follow_up(
        "Use 70%, but only customers with tenure of at least 24 months.",
        current_criteria={
            "contracts": ["Month-to-month", "One year"],
            "minimum_churn_probability": None,
        },
    )

    assert result["kind"] == "unsupported"
    assert "arguments" not in result