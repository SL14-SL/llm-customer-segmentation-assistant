"""Run a bounded segment-comparison agent with visible tool results."""

import json
import math
from collections.abc import Callable
from pathlib import Path
from urllib.request import Request, urlopen

from customer_segmentation_assistant.llm import DEFAULT_MODEL
from customer_segmentation_assistant.tool_dispatch import execute_tool_call
from customer_segmentation_assistant.tools import CONTRACT_TYPES

AGENT_PROMPT = """
Select the next action for a bounded customer-segment comparison.

The application supplies:
- contracts: requested contract types
- remaining_contracts: segments not yet queried
- minimum_churn_probability: the shared inclusive threshold
- observations: completed tool calls and computed results

If remaining_contracts is not empty:
- choose exactly one contract from remaining_contracts
- return {"kind":"tool_call","contract":"the selected contract"}

If remaining_contracts is empty:
- return {"kind":"finish"}

Never request a completed segment.
Do not generate a written comparison.
The application renders the computed statistics.

Return only the JSON action.
"""


def next_action_schema(remaining_contracts: list[str]) -> dict[str, object]:
    """Allow only actions valid for the current execution state."""
    if remaining_contracts:
        return {
            "type": "object",
            "properties": {
                "kind": {"enum": ["tool_call"]},
                "contract": {"enum": list(remaining_contracts)},
            },
            "required": ["kind", "contract"],
            "additionalProperties": False,
        }

    return {
        "type": "object",
        "properties": {
            "kind": {"enum": ["finish"]},
        },
        "required": ["kind"],
        "additionalProperties": False,
    }


def propose_next_action(
    context: dict[str, object],
    *,
    model: str = DEFAULT_MODEL,
) -> dict[str, object]:
    """Propose one next action without executing it."""
    payload = {
        "model": model,
        "system": AGENT_PROMPT,
        "prompt": json.dumps(context, allow_nan=False),
        "format": next_action_schema(context["remaining_contracts"]),
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
        generated = json.load(response)

    if not generated.get("done") or generated.get("done_reason") != "stop":
        raise ValueError("Model did not complete its action normally.")

    raw = generated.get("response")

    if not isinstance(raw, str):
        raise ValueError(  # noqa: TRY004
            "Model returned no action."
        )

    action = json.loads(raw)

    if not isinstance(action, dict):
        raise ValueError(  # noqa: TRY004
            "Agent action must be a JSON object."
        )

    return action


def render_comparison(observations: list[dict[str, object]]) -> str:
    """Render computed segment statistics without model-generated claims."""
    lines = [
        "Comparison of matching customers by contract.",
        "Churn probabilities are predictions, not observed churn outcomes.",
        "Monthly charges have no specified currency.",
    ]

    for observation in observations:
        result = observation["result"]
        threshold = result["minimum_churn_probability"]
        count = result["customer_count"]

        lines.append(
            f"\n{result['contract']} — minimum predicted churn probability: "
            f"{threshold:.1%}; matching customers: {count}."
        )

        if count == 0:
            lines.append("No customers match; averages are unavailable.")
        else:
            lines.append(
                f"Average monthly charges: "
                f"{result['average_monthly_charges']:.2f}. "
                f"Average predicted churn probability: "
                f"{result['average_churn_probability']:.1%}."
            )

    lines.append(
        "\nThese statistics describe only the matching customer segments."
    )
    return "\n".join(lines)


def run_comparison(
    *,
    contracts: tuple[str, ...],
    minimum_churn_probability: float,
    database: Path,
    max_tool_calls: int = 4,
    planner: Callable[[dict[str, object]], dict[str, object]] = (
        propose_next_action
    ),
) -> dict[str, object]:
    """Execute permitted actions until completion or a limit violation."""
    if (
        len(contracts) < 2
        or any(
            not isinstance(contract, str) or contract not in CONTRACT_TYPES
            for contract in contracts
        )
        or len(set(contracts)) != len(contracts)
    ):
        raise ValueError("Supply at least two distinct supported contracts.")

    if (
        isinstance(minimum_churn_probability, bool)
        or not isinstance(minimum_churn_probability, (int, float))
        or not math.isfinite(minimum_churn_probability)
        or not 0 <= minimum_churn_probability <= 1
    ):
        raise ValueError("Probability threshold must be from 0 to 1.")

    if (
        isinstance(max_tool_calls, bool)
        or not isinstance(max_tool_calls, int)
        or max_tool_calls < 1
    ):
        raise ValueError("max_tool_calls must be a positive integer.")

    threshold = float(minimum_churn_probability)
    observations = []
    completed = set()

    # Allow at most max_tool_calls tool executions and one final model turn.
    for _ in range(max_tool_calls + 1):
        context = {
            "contracts": list(contracts),
            "remaining_contracts": [
                contract
                for contract in contracts
                if contract not in completed
            ],
            "minimum_churn_probability": threshold,
            "observations": observations,
        }

        # Give the planner a detached copy of application state.
        action = planner(json.loads(json.dumps(context)))

        if not isinstance(action, dict):
            raise ValueError(  # noqa: TRY004
                "Agent action must be a JSON object."
            )

        if action.get("kind") == "finish":
            if set(action) != {"kind"}:
                raise ValueError("Unexpected finish fields.")

            if completed != set(contracts):
                raise ValueError("Agent finished before comparing all segments.")

            return {
                "answer": render_comparison(observations),
                "observations": observations,
                "tool_calls": len(observations),
            }

        if (
            action.get("kind") != "tool_call"
            or set(action) != {"kind", "contract"}
        ):
            raise ValueError("Unsupported agent action.")

        contract = action["contract"]

        if not isinstance(contract, str) or contract not in contracts:
            raise ValueError("Agent requested a contract outside the scope.")

        if contract in completed:
            raise ValueError("Agent requested a completed segment again.")

        if len(observations) >= max_tool_calls:
            raise RuntimeError("Agent tool-call limit reached.")

        call = {
            "tool": "summarize_segment",
            "arguments": {
                "contract": contract,
                "minimum_churn_probability": threshold,
            },
        }
        result = execute_tool_call(
            json.dumps(call),
            database=database,
        )
        observations.append({
            "call": call,
            "result": result,
        })
        completed.add(contract)

    raise RuntimeError("Agent step limit reached.")