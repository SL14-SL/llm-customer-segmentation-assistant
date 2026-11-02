"""Verify criteria validation and deterministic clarification decisions."""

import json

import pytest

from customer_segmentation_assistant.tool_llm import (
    parse_segment_criteria,
    parse_tool_decision,
)


@pytest.mark.parametrize(
    ("contract", "threshold", "expected_question"),
    [
        (
            None,
            None,
            "Which contract type and minimum churn probability should I use?",
        ),
        (
            None,
            0.55,
            "Which contract type should I use?",
        ),
        (
            "Two year",
            None,
            "Which minimum churn probability should I use?",
        ),
    ],
)
def test_asks_only_for_missing_criteria(
    contract,
    threshold,
    expected_question,
):
    raw = json.dumps({
        "contract": contract,
        "minimum_churn_probability": threshold,
    })

    assert parse_tool_decision(raw) == {
        "kind": "clarification",
        "question": expected_question,
    }


@pytest.mark.parametrize("threshold", [0.0, 0.65, 1.0])
def test_complete_criteria_create_tool_call(threshold):
    criteria = {
        "contract": "Month-to-month",
        "minimum_churn_probability": threshold,
    }

    assert parse_tool_decision(json.dumps(criteria)) == {
        "kind": "tool_call",
        "tool": "summarize_segment",
        "arguments": criteria,
    }


def test_zero_threshold_with_missing_contract_asks_only_for_contract():
    raw = json.dumps({
        "contract": None,
        "minimum_churn_probability": 0.0,
    })

    assert parse_tool_decision(raw) == {
        "kind": "clarification",
        "question": "Which contract type should I use?",
    }


@pytest.mark.parametrize(
    "raw",
    [
        "invalid",
        "[]",
        "{}",
        '{"contract":"One year"}',
        '{"contract":null,"minimum_churn_probability":null,"extra":1}',
        '{"contract":"unsupported","minimum_churn_probability":0.5}',
        '{"contract":[],"minimum_churn_probability":0.5}',
        '{"contract":"One year","minimum_churn_probability":"0.5"}',
        '{"contract":"One year","minimum_churn_probability":true}',
        '{"contract":"One year","minimum_churn_probability":-0.1}',
        '{"contract":"One year","minimum_churn_probability":1.1}',
        '{"contract":"One year","minimum_churn_probability":NaN}',
        '{"contract":"One year","minimum_churn_probability":Infinity}',
    ],
)
def test_rejects_invalid_criteria(raw):
    with pytest.raises(ValueError):
        parse_segment_criteria(raw)