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


def test_unsupported_request_has_no_execution_arguments():
    result = parse_comparison_request(json.dumps({
        "kind": "unsupported",
        "message": "Tenure filters are not supported.",
    }))

    assert result["kind"] == "unsupported"
    assert "arguments" not in result