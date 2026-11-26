"""Verify deterministic comparison scope checks."""

import pytest

from customer_segmentation_assistant import comparison_request
from customer_segmentation_assistant.comparison_conversation import (
    ComparisonConversation,
)
from customer_segmentation_assistant.comparison_scope import (
    check_comparison_scope,
    detect_unsupported_requirements,
)


@pytest.mark.parametrize(
    "question",
    [
        "Compare customers with tenure of at least 24 months.",
        "Compare customers who have been with the company for two years.",
        "Compare customers for more than two years.",
        "Compare annual contracts with customer tenure above 12 months.",
        "Compare monthly charges above $80.",
        "Compare customers with monthly charges at least 80 dollars.",
        "Compare customers with monthly charges >= 80.",
        "Compare customers paying more than $80.",
        "Compare customers based on age.",
        "Compare customers based on gender.",
        "Compare customers by payment method.",
        "Compare customers based on internet service.",
        "Compare customers with total charges above 1000.",
        (
            "Compare monthly and annual contracts with churn probability "
            "at least 60%, but only customers with tenure of at least "
            "24 months."
        ),
        (
            "Use a minimum predicted churn probability of 81%, "
            "but only include customers with tenure of at least "
            "24 months."
        ),
    ],
)
def test_detects_unsupported_requirements(question):
    requirements = detect_unsupported_requirements(question)

    assert requirements
    assert check_comparison_scope(question)["kind"] == "unsupported"


@pytest.mark.parametrize(
    "question",
    [
        "Compare monthly and annual contracts.",
        "Compare one-year and two-year contracts.",
        "Compare all three contract types.",
        "Use a minimum churn probability of 70%.",
        "Use a minimum churn probability of 0%.",
        "Compare average monthly charges.",
        "Show the average predicted churn probability.",
        "Compare customer counts.",
        (
            "Compare monthly and annual contracts with churn "
            "probability of at least 60%."
        ),
        (
            "Compare one-year and two-year contracts. Include only "
            "customers with a predicted churn probability of at least 95%."
        ),
    ],
)
def test_supported_requests_are_not_blocked(question):
    assert detect_unsupported_requirements(question) == []
    assert check_comparison_scope(question) is None


def test_detects_multiple_unsupported_requirements():
    requirements = detect_unsupported_requirements(
        "Compare customers with tenure above 24 months and monthly charges above $80."
    )

    assert len(requirements) == 2


def test_unsupported_request_does_not_call_ollama(monkeypatch):
    def unexpected_model_call(*args, **kwargs):
        pytest.fail("Ollama must not be called for unsupported requests.")

    monkeypatch.setattr(
        comparison_request,
        "urlopen",
        unexpected_model_call,
    )

    result = comparison_request.extract_comparison_criteria(
        "Compare monthly and annual contracts with tenure above 24 months."
    )

    assert result["kind"] == "unsupported"


def test_unsupported_follow_up_does_not_call_ollama(monkeypatch):
    def unexpected_model_call(*args, **kwargs):
        pytest.fail("Ollama must not be called for unsupported follow-ups.")

    monkeypatch.setattr(
        comparison_request,
        "urlopen",
        unexpected_model_call,
    )

    conversation = ComparisonConversation()

    conversation.update(
        {
            "contracts": ["One year", "Two year"],
            "minimum_churn_probability": None,
        }
    )

    extracted = comparison_request.extract_comparison_follow_up(
        "Use 81% but only customers with tenure above 24 months.",
        current_criteria=conversation.criteria,
    )

    result = conversation.update(extracted)

    assert result["kind"] == "unsupported"


def test_unsupported_scope_remains_blocked():
    conversation = ComparisonConversation()

    unsupported = check_comparison_scope(
        "Compare customers with tenure above 24 months."
    )

    first = conversation.update(unsupported)

    second = conversation.update(
        {
            "contracts": ["One year", "Two year"],
            "minimum_churn_probability": 0.7,
        }
    )

    assert first["kind"] == "unsupported"
    assert second == first
