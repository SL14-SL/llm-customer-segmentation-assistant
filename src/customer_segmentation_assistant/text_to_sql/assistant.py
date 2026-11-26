"""Generate validated assistant decisions using local Ollama."""

from customer_segmentation_assistant.config import DEFAULT_MODEL
from customer_segmentation_assistant.llm.client import generate_structured_response
from customer_segmentation_assistant.text_to_sql.decisions import (
    ClarificationDecision,
    QueryDecision,
    UnsupportedDecision,
    parse_decision,
)
from customer_segmentation_assistant.text_to_sql.prompts import SYSTEM_PROMPT
from customer_segmentation_assistant.text_to_sql.row_limits import enforce_row_limit

DECISION_SCHEMA = {
    "anyOf": [
        {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": ["query"]},
                "sql": {"type": "string"},
            },
            "required": ["kind", "sql"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "kind": {
                    "type": "string",
                    "enum": ["clarification"],
                },
                "question": {"type": "string"},
            },
            "required": ["kind", "question"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "kind": {
                    "type": "string",
                    "enum": ["unsupported"],
                },
                "message": {"type": "string"},
            },
            "required": ["kind", "message"],
            "additionalProperties": False,
        },
    ]
}


def generate_decision(
    question: str,
    *,
    model: str = DEFAULT_MODEL,
    customer_messages: list[str] | None = None,
) -> QueryDecision | ClarificationDecision | UnsupportedDecision:
    """Generate one decision without executing SQL."""
    if not question.strip():
        raise ValueError("Question must not be empty.")

    raw = generate_structured_response(
        system=SYSTEM_PROMPT,
        prompt=question,
        schema=DECISION_SCHEMA,
        model=model,
        num_predict=512,
    )

    decision = parse_decision(raw)

    if isinstance(decision, QueryDecision):
        return enforce_row_limit(
            decision,
            customer_messages if customer_messages is not None else [question],
        )

    return decision