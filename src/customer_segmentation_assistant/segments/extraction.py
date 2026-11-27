"""Extract segment criteria and determine the next action in Python."""

import json

from customer_segmentation_assistant.config import DEFAULT_MODEL
from customer_segmentation_assistant.llm.client import generate_structured_response
from customer_segmentation_assistant.segments.criteria import (
    parse_segment_criteria,
)

CRITERIA_SCHEMA = {
    "type": "object",
    "properties": {
        "contract": {
            "enum": [
                "Month-to-month",
                "One year",
                "Two year",
                None,
            ],
        },
        "minimum_churn_probability": {
            "type": ["number", "null"],
            "minimum": 0,
            "maximum": 1,
        },
    },
    "required": ["contract", "minimum_churn_probability"],
    "additionalProperties": False,
}

CRITERIA_SYSTEM_PROMPT = """
Extract explicitly supplied customer-segment criteria from an English request.

Return exactly one JSON object with these two fields:
- contract
- minimum_churn_probability

Contract values:
- monthly or month-to-month contracts: "Month-to-month"
- annual, yearly or one-year contracts: "One year"
- two-year contracts: "Two year"
- no supported contract explicitly supplied: null

Minimum churn probability:
- extract an explicitly stated inclusive minimum
- "at least", "minimum" and "or higher" express an inclusive minimum
- convert percentages to probabilities
- 65% means 0.65
- 0% means 0.0 and is not missing information
- no explicit numerical minimum: null

Never supply a default contract or risk threshold.
"High risk" alone does not specify a numerical minimum.
Use JSON null for missing criteria, not the string "null".
Do not ask questions, generate SQL, calculate metrics or execute tools.
"""


def parse_tool_decision(raw: str) -> dict[str, object]:
    """Turn extracted criteria into a deterministic next action."""
    criteria = parse_segment_criteria(raw)
    contract_missing = criteria["contract"] is None
    threshold_missing = criteria["minimum_churn_probability"] is None

    if contract_missing and threshold_missing:
        question = "Which contract type and minimum churn probability should I use?"
    elif contract_missing:
        question = "Which contract type should I use?"
    elif threshold_missing:
        question = "Which minimum churn probability should I use?"
    else:
        return {
            "kind": "tool_call",
            "tool": "summarize_segment",
            "arguments": criteria,
        }

    return {
        "kind": "clarification",
        "question": question,
    }


def extract_segment_criteria(
    question: str,
    *,
    model: str = DEFAULT_MODEL,
) -> dict[str, object]:
    """Extract supplied criteria without executing a tool."""
    if not question.strip():
        raise ValueError("Question must not be empty.")

    raw = generate_structured_response(
        system=CRITERIA_SYSTEM_PROMPT,
        prompt=question,
        schema=CRITERIA_SCHEMA,
        model=model,
        num_predict=256,
    )

    return parse_segment_criteria(raw)


def generate_tool_decision(
    question: str,
    *,
    model: str = DEFAULT_MODEL,
) -> dict[str, object]:
    """Extract criteria and determine the next action."""
    criteria = extract_segment_criteria(question, model=model)
    return parse_tool_decision(json.dumps(criteria))
