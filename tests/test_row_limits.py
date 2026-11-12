"""Check customer-requested limits independently of model behavior."""

import pytest
from sqlglot import parse_one

from customer_segmentation_assistant.decisions import (
    ClarificationDecision,
    QueryDecision,
)
from customer_segmentation_assistant.row_limits import enforce_row_limit


@pytest.mark.parametrize(
    ("messages", "expected_limit"),
    [
        (["Show me high-risk customers.", "At least 90%."], None),
        (["Show me high-risk customers.", "At least 90%. Top 5."], 5),
        (["Show the top 5 high-risk customers.", "At least 90%."], 5),
        (["Show the top 5 customers.", "Show all matching customers."], None),
        (["Show the top 5 customers.", "Limit to 3."], 3),
        (["Show 7 customers."], 7),
        (["Customers with at least 24 months tenure and 90% risk."], None),
    ],
)
def test_enforces_customer_limit(messages, expected_limit):
    decision = QueryDecision(
        sql=(
            "SELECT customerID, churn_probability FROM customers "
            "WHERE churn_probability >= 0.9 "
            "ORDER BY churn_probability DESC, customerID LIMIT 10"
        )
    )

    result = enforce_row_limit(decision, messages)

    assert isinstance(result, QueryDecision)
    query = parse_one(result.sql, read="duckdb")
    limit = query.args.get("limit")

    if expected_limit is None:
        assert limit is None
    else:
        assert int(limit.expression.this) == expected_limit

    assert query.args.get("where") is not None
    assert query.args.get("order") is not None


def test_adds_requested_limit_when_model_omits_it():
    result = enforce_row_limit(
        QueryDecision(sql="SELECT customerID FROM customers ORDER BY customerID"),
        ["Show the top 5 customers."],
    )

    assert isinstance(result, QueryDecision)
    query = parse_one(result.sql, read="duckdb")
    assert int(query.args["limit"].expression.this) == 5


def test_conflicting_counts_require_clarification():
    result = enforce_row_limit(
        QueryDecision(sql="SELECT customerID FROM customers LIMIT 10"),
        ["Show top 5 or top 10 customers."],
    )

    assert isinstance(result, ClarificationDecision)