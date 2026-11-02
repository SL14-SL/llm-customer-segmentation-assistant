"""Validate and execute explicitly supported tool calls."""

import json
from pathlib import Path

from customer_segmentation_assistant.tools import summarize_segment


def execute_tool_call(
    raw: str,
    *,
    database: Path,
) -> dict[str, int | float | str | None]:
    """Execute one validated segment-summary call."""
    try:
        call = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("Tool call must be valid JSON.") from error

    if not isinstance(call, dict):
        raise ValueError( # noqa: TRY004
            "Tool call must be a JSON object."
        )

    if set(call) != {"tool", "arguments"}:
        raise ValueError("Tool call requires exactly tool and arguments.")

    if call["tool"] != "summarize_segment":
        raise ValueError("Unsupported tool.")

    arguments = call["arguments"]

    if not isinstance(arguments, dict):
        raise ValueError( # noqa: TRY004
            "Tool arguments must be a JSON object."
        )

    if set(arguments) != {"contract", "minimum_churn_probability"}:
        raise ValueError("Unexpected or missing tool arguments.")

    return summarize_segment(
        contract=arguments["contract"],
        minimum_churn_probability=arguments["minimum_churn_probability"],
        database=database,
    )