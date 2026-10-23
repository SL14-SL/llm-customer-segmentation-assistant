"""Parse and validate structured assistant decisions."""

import json
from dataclasses import dataclass

from customer_segmentation_assistant.sql_policy import validate_sql


@dataclass(frozen=True)
class QueryDecision:
    sql: str


@dataclass(frozen=True)
class ClarificationDecision:
    question: str

@dataclass(frozen=True)
class UnsupportedDecision:
    message: str

def parse_decision(
    raw: str,
) -> QueryDecision | ClarificationDecision | UnsupportedDecision:
    """Accept exactly one supported decision from a JSON response."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("Assistant response must be valid JSON.") from error

    if not isinstance(payload, dict):
        raise ValueError("Assistant response must be a JSON object.")  # noqa: TRY004 - invalid response format

    kind = payload.get("kind")

    if kind == "query":
        field = "sql"
    elif kind == "clarification":
        field = "question"
    elif kind == "unsupported":
        field = "message"
    else:
        raise ValueError("Unknown decision kind.")

    if set(payload) != {"kind", field}:
        raise ValueError("Unexpected or missing decision fields.")

    value = payload[field]

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string.")

    value = value.strip()

    if kind == "query":
        validate_sql(value)
        return QueryDecision(sql=value)

    if kind == "unsupported":
        return UnsupportedDecision(message=value)

    return ClarificationDecision(question=value)
