"""Verify structured assistant response handling."""

import json

import pytest

from customer_segmentation_assistant.decisions import (
    ClarificationDecision,
    QueryDecision,
    UnsupportedDecision,
    parse_decision,
)


def test_accepts_query():
    sql = "SELECT COUNT(*) AS customer_count FROM customers"

    decision = parse_decision(json.dumps({"kind": "query", "sql": sql}))

    assert decision == QueryDecision(sql=sql)


def test_accepts_clarification():
    question = "Which minimum churn probability defines high risk?"

    decision = parse_decision(
        json.dumps({"kind": "clarification", "question": question})
    )

    assert decision == ClarificationDecision(question=question)


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        "[]",
        '{"kind": "unknown"}',
        '{"kind": "query"}',
        '{"kind": "query", "sql": ""}',
        '{"kind": "query", "sql": 123}',
        '{"kind": "query", "sql": "DELETE FROM customers"}',
        '{"kind": "query", "sql": "SELECT * FROM other"}',
        '{"kind": "clarification", "question": "   "}',
        '{"kind": "clarification", "question": "Which risk?", "sql": "SELECT 1"}',
    ],
)
def test_rejects_invalid_response(raw):
    with pytest.raises(ValueError):
        parse_decision(raw)


def test_accepts_unsupported_response():
    message = "Weather information is not available."

    decision = parse_decision(
        json.dumps({"kind": "unsupported", "message": message})
    )

    assert decision == UnsupportedDecision(message=message)


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "unsupported", "message": ""},
        {"kind": "unsupported", "message": 123},
        {
            "kind": "unsupported",
            "message": "Unavailable.",
            "sql": "SELECT * FROM customers",
        },
    ],
)
def test_rejects_invalid_unsupported_response(payload):
    with pytest.raises(ValueError):
        parse_decision(json.dumps(payload))