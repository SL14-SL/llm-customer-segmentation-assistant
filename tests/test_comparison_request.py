"""Verify comparison scope validation independently of the model."""

import json

import pytest

from customer_segmentation_assistant.comparison_request import (
    parse_comparison_request,
)


def test_complete_scope_preserves_zero_threshold():
    result = parse_comparison_request(json.dumps({
        "contracts": ["Month-to-month", "One year"],
        "minimum_churn_probability": 0.0,
    }))

    assert result == {
        "kind": "comparison",
        "arguments": {
            "contracts": ["Month-to-month", "One year"],
            "minimum_churn_probability": 0.0,
        },
    }


@pytest.mark.parametrize(
    ("contracts", "threshold", "question"),
    [
        (
            [],
            None,
            (
                "Which at least two contract types and minimum churn "
                "probability should I use?"
            ),
        ),
        (
            ["One year"],
            0.7,
            "Which at least two contract types should I compare?",
        ),
        (
            ["One year", "Two year"],
            None,
            "Which minimum churn probability should I use?",
        ),
    ],
)
def test_missing_criteria_produce_clarification(
    contracts,
    threshold,
    question,
):
    result = parse_comparison_request(json.dumps({
        "contracts": contracts,
        "minimum_churn_probability": threshold,
    }))

    assert result == {"kind": "clarification", "question": question}


@pytest.mark.parametrize(
    "raw",
    [
        "[]",
        "{}",
        '{"contracts":"One year","minimum_churn_probability":0.7}',
        '{"contracts":["Other"],"minimum_churn_probability":0.7}',
        '{"contracts":[[]],"minimum_churn_probability":0.7}',
        (
            '{"contracts":["One year","One year"],'
            '"minimum_churn_probability":0.7}'
        ),
        (
            '{"contracts":["One year","Two year"],'
            '"minimum_churn_probability":70}'
        ),
        (
            '{"contracts":["One year","Two year"],'
            '"minimum_churn_probability":true}'
        ),
    ],
)
def test_rejects_invalid_scope(raw):
    with pytest.raises(ValueError):
        parse_comparison_request(raw)

def test_unsupported_requirement_is_preserved():
    result = parse_comparison_request(json.dumps({
        "kind": "unsupported",
        "message": "Tenure filters are not supported.",
    }))

    assert result == {
        "kind": "unsupported",
        "message": "Tenure filters are not supported.",
    }


@pytest.mark.parametrize(
    "decision",
    [
        {"kind": "unsupported", "message": ""},
        {"kind": "unsupported", "message": 42},
        {"kind": "unsupported", "message": "Unsupported", "extra": True},
    ],
)
def test_rejects_invalid_unsupported_decisions(decision):
    with pytest.raises(ValueError):
        parse_comparison_request(json.dumps(decision))


def test_unsupported_follow_up_blocks_later_execution():
    from customer_segmentation_assistant.comparison_conversation import (
        ComparisonConversation,
    )

    conversation = ComparisonConversation()

    assert conversation.update({
        "contracts": ["Month-to-month", "One year"],
        "minimum_churn_probability": None,
    })["kind"] == "clarification"

    rejected = conversation.update({
        "kind": "unsupported",
        "message": "Tenure filters are not supported.",
    })

    assert rejected["kind"] == "unsupported"

    assert conversation.update({
        "contracts": [],
        "minimum_churn_probability": 0.6,
    }) == rejected

@pytest.mark.parametrize(
    ("probabilities", "requirements"),
    [
        ([0.4, 0.75], []),
        ([0.81], ["Only customers with tenure of at least 24 months"]),
    ],
)
def test_extracted_requirements_block_incomplete_comparison(
    probabilities,
    requirements,
):
    from customer_segmentation_assistant.comparison_request import (
        normalize_comparison_extraction,
    )

    result = normalize_comparison_extraction(json.dumps({
        "contracts": ["Month-to-month", "One year"],
        "minimum_probabilities": probabilities,
        "unsupported_requirements": requirements,
    }))

    assert result["kind"] == "unsupported"


def test_same_threshold_for_both_contracts_is_supported():
    from customer_segmentation_assistant.comparison_request import (
        normalize_comparison_extraction,
    )

    result = normalize_comparison_extraction(json.dumps({
        "contracts": ["Month-to-month", "One year"],
        "minimum_probabilities": [0.6, 0.6],
        "unsupported_requirements": [],
    }))

    assert result == {
        "contracts": ["Month-to-month", "One year"],
        "minimum_churn_probability": 0.6,
    }