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
            "contracts": ["Two year"],
            "minimum_churn_probability": 0.7,
        }

    monkeypatch.setattr(
        comparison_request,
        "extract_comparison_criteria",
        fake_extraction,
    )

    extracted = comparison_request.extract_comparison_follow_up(
        "At least 70%.",
        current_criteria=conversation.criteria,
        model="test-model",
    )
    decision = conversation.update(extracted)

    assert decision == {
        "kind": "comparison",
        "arguments": {
            "contracts": ["Month-to-month", "One year"],
            "minimum_churn_probability": 0.7,
        },
    }