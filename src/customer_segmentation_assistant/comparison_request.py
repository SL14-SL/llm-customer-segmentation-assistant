"""Extract and validate the scope of a contract comparison."""

import json
from urllib.request import Request, urlopen

from customer_segmentation_assistant.llm import DEFAULT_MODEL
from customer_segmentation_assistant.tool_llm import (
    extract_segment_criteria,
    parse_segment_criteria,
)
from customer_segmentation_assistant.tools import CONTRACT_TYPES

COMPARISON_SCHEMA = {
    "type": "object",
    "properties": {
        "contracts": {
            "type": "array",
            "items": {
                "enum": ["Month-to-month", "One year", "Two year"],
            },
            "maxItems": 3,
            "uniqueItems": True,
        },
        "minimum_churn_probability": {
            "type": ["number", "null"],
            "minimum": 0,
            "maximum": 1,
        },
    },
    "required": ["contracts", "minimum_churn_probability"],
    "additionalProperties": False,
}

COMPARISON_PROMPT = """
Extract the scope of a customer comparison by contract type.

Return only:
{"contracts":[...],"minimum_churn_probability":...}

Supported contracts:
- monthly or month-to-month: "Month-to-month"
- annual, yearly or one-year: "One year"
- two-year: "Two year"

Include only explicitly requested contract types.
Do not add a contract to make a comparison possible.
Use an empty list if no contract types are supplied.
Do not repeat contracts.

Extract one explicitly supplied inclusive minimum predicted churn probability.
"At least", "minimum" and "or higher" specify an inclusive minimum.
Convert percentages to probabilities.
0% is 0.0, not missing information.
Use null if no numerical minimum is supplied.
"High risk" alone does not specify a threshold.

Do not execute tools, ask questions or calculate results.
"""


def parse_comparison_request(raw: str) -> dict[str, object]:
    """Validate extracted scope and request missing comparison criteria."""
    try:
        criteria = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("Comparison criteria must be valid JSON.") from error

    if not isinstance(criteria, dict):
        raise ValueError(  # noqa: TRY004
            "Comparison criteria must be a JSON object."
        )

    if set(criteria) != {"contracts", "minimum_churn_probability"}:
        raise ValueError("Unexpected or missing comparison fields.")

    contracts = criteria["contracts"]

    if not isinstance(contracts, list):
        raise ValueError(  # noqa: TRY004
            "Contracts must be a list."
        )

    if any(
        not isinstance(contract, str) or contract not in CONTRACT_TYPES
        for contract in contracts
    ):
        raise ValueError("Unsupported comparison contract.")

    if len(set(contracts)) != len(contracts):
        raise ValueError("Comparison contracts must be distinct.")

    validated = parse_segment_criteria(json.dumps({
        "contract": None,
        "minimum_churn_probability": criteria["minimum_churn_probability"],
    }))
    threshold = validated["minimum_churn_probability"]

    if len(contracts) < 2 and threshold is None:
        question = (
            "Which at least two contract types and minimum churn "
            "probability should I use?"
        )
    elif len(contracts) < 2:
        question = "Which at least two contract types should I compare?"
    elif threshold is None:
        question = "Which minimum churn probability should I use?"
    else:
        return {
            "kind": "comparison",
            "arguments": {
                "contracts": list(contracts),
                "minimum_churn_probability": threshold,
            },
        }

    return {
        "kind": "clarification",
        "question": question,
    }


def extract_comparison_criteria(
    question: str,
    *,
    model: str = DEFAULT_MODEL,
) -> dict[str, object]:
    """Extract comparison criteria without executing database queries."""
    if not question.strip():
        raise ValueError("Question must not be empty.")

    payload = {
        "model": model,
        "system": COMPARISON_PROMPT,
        "prompt": question,
        "format": COMPARISON_SCHEMA,
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
        generated = json.load(response)

    if not generated.get("done") or generated.get("done_reason") != "stop":
        raise ValueError("Model did not complete its extraction normally.")

    raw = generated.get("response")

    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Model returned no comparison criteria.")

    # Validate before exposing the extracted criteria.
    parse_comparison_request(raw)
    return json.loads(raw)


def generate_comparison_request(
    question: str,
    *,
    model: str = DEFAULT_MODEL,
) -> dict[str, object]:
    """Extract comparison criteria and determine the next action."""
    criteria = extract_comparison_criteria(question, model=model)
    return parse_comparison_request(json.dumps(criteria))


def extract_comparison_follow_up(
    question: str,
    *,
    current_criteria: dict[str, object],
    model: str = DEFAULT_MODEL,
) -> dict[str, object]:
    """Extract the missing threshold without changing known contracts."""
    contracts = current_criteria["contracts"]
    threshold = current_criteria["minimum_churn_probability"]

    if len(contracts) >= 2 and threshold is None:
        extracted = extract_segment_criteria(question, model=model)

        return {
            "contracts": [],
            "minimum_churn_probability": (
                extracted["minimum_churn_probability"]
            ),
        }

    return extract_comparison_criteria(question, model=model)