"""Translate one explicit segment request into a structured tool call."""

import json
from urllib.request import Request, urlopen

from customer_segmentation_assistant.llm import DEFAULT_MODEL

TOOL_CALL_SCHEMA = {
    "type": "object",
    "properties": {
        "tool": {
            "type": "string",
            "enum": ["summarize_segment"],
        },
        "arguments": {
            "type": "object",
            "properties": {
                "contract": {
                    "type": "string",
                    "enum": ["Month-to-month", "One year", "Two year"],
                },
                "minimum_churn_probability": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                },
            },
            "required": ["contract", "minimum_churn_probability"],
            "additionalProperties": False,
        },
    },
    "required": ["tool", "arguments"],
    "additionalProperties": False,
}

TOOL_SYSTEM_PROMPT = """
Translate an explicit English customer-segment request into one tool call.

Available tool:
summarize_segment(contract, minimum_churn_probability)

The tool returns customer count, average monthly charges and average
predicted churn probability for matching customers.

Supported contract values:
- Month-to-month
- One year
- Two year

The probability threshold is inclusive.
Convert percentages to probabilities: 65% means 0.65.
Use the contract and threshold supplied by the user.
Return only the JSON tool call. Do not generate SQL or calculate results.

Example request:
Summarize monthly-contract customers with churn probability at least 80%.

Example response:
{"tool":"summarize_segment","arguments":{"contract":"Month-to-month",
"minimum_churn_probability":0.8}}
"""


def generate_tool_call(
    question: str,
    *,
    model: str = DEFAULT_MODEL,
) -> str:
    """Generate a tool-call proposal without executing it."""
    if not question.strip():
        raise ValueError("Question must not be empty.")

    payload = {
        "model": model,
        "system": TOOL_SYSTEM_PROMPT,
        "prompt": question,
        "format": TOOL_CALL_SCHEMA,
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
        raise ValueError("Local model returned no tool call.")

    return raw