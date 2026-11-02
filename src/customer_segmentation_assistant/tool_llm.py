"""Extract segment criteria and determine the next action in Python."""

import json
import math
from urllib.request import Request, urlopen

from customer_segmentation_assistant.llm import DEFAULT_MODEL
from customer_segmentation_assistant.tools import CONTRACT_TYPES

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


def parse_segment_criteria(raw: str) -> dict[str, object]:
    """Validate extracted criteria without accessing customer data."""
    try:
        criteria = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("Criteria must be valid JSON.") from error

    if not isinstance(criteria, dict):
        raise ValueError(  # noqa: TRY004
            "Criteria must be a JSON object."
        )

    if set(criteria) != {"contract", "minimum_churn_probability"}:
        raise ValueError("Unexpected or missing criteria fields.")

    contract = criteria["contract"]

    if contract is not None and (
        not isinstance(contract, str) or contract not in CONTRACT_TYPES
    ):
        raise ValueError("Unsupported contract type.")

    threshold = criteria["minimum_churn_probability"]

    if threshold is not None:
        if (
            isinstance(threshold, bool)
            or not isinstance(threshold, (int, float))
            or not math.isfinite(threshold)
            or not 0 <= threshold <= 1
        ):
            raise ValueError(
                "Minimum probability must be a finite number from 0 to 1."
            )

        threshold = float(threshold)

    return {
        "contract": contract,
        "minimum_churn_probability": threshold,
    }


def parse_tool_decision(raw: str) -> dict[str, object]:
    """Turn extracted criteria into a deterministic next action."""
    criteria = parse_segment_criteria(raw)
    contract_missing = criteria["contract"] is None
    threshold_missing = criteria["minimum_churn_probability"] is None

    if contract_missing and threshold_missing:
        question = (
            "Which contract type and minimum churn probability should I use?"
        )
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


def generate_tool_decision(
    question: str,
    *,
    model: str = DEFAULT_MODEL,
) -> dict[str, object]:
    """Extract criteria and propose an action without executing it."""
    if not question.strip():
        raise ValueError("Question must not be empty.")

    payload = {
        "model": model,
        "system": CRITERIA_SYSTEM_PROMPT,
        "prompt": question,
        "format": CRITERIA_SCHEMA,
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "temperature": 0,
            "num_ctx": 4096,
            "num_predict": 256,
        },
    }

    request = Request(
        "http://localhost:11434/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request, timeout=180) as response:
        result = json.load(response)

    if not result.get("done") or result.get("done_reason") != "stop":
        raise ValueError("Local model did not complete its response normally.")

    raw = result.get("response")

    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Local model returned no segment criteria.")

    return parse_tool_decision(raw)