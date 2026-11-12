"""Apply explicit customer-list limits independently of generated SQL."""

import re

from sqlglot import exp, parse_one

from customer_segmentation_assistant.decisions import (
    ClarificationDecision,
    QueryDecision,
)
from customer_segmentation_assistant.sql_policy import validate_sql

COUNT_PATTERNS = (
    r"\b(?:top|bottom|first|last)\s+([1-9]\d*)\b",
    (
        r"\b(?:show|return|list|give)(?:\s+me)?\s+(?:the\s+)?([1-9]\d*)"
        r"\s+(?:customers?|rows?|records?|results?)\b"
    ),
    r"\blimit(?:\s+(?:it|results?|customers?))?\s+(?:to\s+)?([1-9]\d*)\b",
)

ALL_PATTERN = (
    r"\b(?:all|every)\s+(?:(?:the|matching)\s+)*"
    r"(?:customers?|rows?|records?|results?)\b"
    r"|\b(?:no|without)\s+(?:a\s+)?limit\b"
)


def enforce_row_limit(
    decision: QueryDecision,
    customer_messages: list[str],
) -> QueryDecision | ClarificationDecision:
    """Enforce supported count phrases, retaining counts across clarifications."""
    requested_limit = None

    for message in customer_messages:
        counts = {
            int(match.group(1))
            for pattern in COUNT_PATTERNS
            for match in re.finditer(pattern, message, re.IGNORECASE)
        }
        wants_all = re.search(ALL_PATTERN, message, re.IGNORECASE) is not None

        if len(counts) > 1 or (counts and wants_all):
            return ClarificationDecision(
                question=(
                    "Please specify one result limit, such as 'top 5', "
                    "or say 'all matching customers'."
                )
            )

        if wants_all:
            requested_limit = None
        elif counts:
            requested_limit = counts.pop()

    # Validate the original SQL before modifying its syntax tree.
    validate_sql(decision.sql)
    query = parse_one(decision.sql, read="duckdb")

    if not isinstance(query, exp.Select):
        raise TypeError("Expected a SELECT query.")

    if query.args.get("offset") is not None:
        raise ValueError("Result offsets are not supported.")

    # Remove any model-invented limit, then apply the customer's limit.
    query.set("limit", None)
    if requested_limit is not None:
        query = query.limit(requested_limit)

    sql = query.sql(dialect="duckdb")
    validate_sql(sql)
    return QueryDecision(sql=sql)