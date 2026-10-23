"""Generate validated assistant decisions using local Ollama."""

import json
from urllib.request import Request, urlopen

from customer_segmentation_assistant.decisions import (
    ClarificationDecision,
    QueryDecision,
    UnsupportedDecision,
    parse_decision,
)
from customer_segmentation_assistant.prompts import SYSTEM_PROMPT

DEFAULT_MODEL = "qwen2.5-coder:3b"

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
) -> QueryDecision | ClarificationDecision | UnsupportedDecision:
    """Generate one decision without executing SQL."""
    if not question.strip():
        raise ValueError("Question must not be empty.")

    payload = {
        "model": model,
        "system": SYSTEM_PROMPT,
        "prompt": question,
        "format": DECISION_SCHEMA,
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "temperature": 0,
            "num_ctx": 4096,
            "num_predict": 512,
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

    return parse_decision(result["response"])
