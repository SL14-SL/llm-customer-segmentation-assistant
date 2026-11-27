"""Verify deterministic comparison execution without model inference."""

import argparse
from pathlib import Path

from customer_segmentation_assistant.comparison.agent import (
    run_comparison,
)
from customer_segmentation_assistant.demo.comparison import (
    create_demo_database,
)


def deterministic_planner(
    context: dict[str, object],
) -> dict[str, object]:
    """Select the next outstanding contract without an LLM."""
    remaining = context["remaining_contracts"]

    if remaining:
        return {
            "kind": "tool_call",
            "contract": remaining[0],
        }

    return {"kind": "finish"}


def main() -> None:
    """Verify comparison tools and the computed report."""
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--database",
        type=Path,
        required=True,
        help="Path to an isolated synthetic comparison database.",
    )

    args = parser.parse_args()
    database = args.database

    if database.exists():
        raise SystemExit(f"Smoke-test database already exists: {database}")

    create_demo_database(database)

    result = run_comparison(
        contracts=("Month-to-month", "One year"),
        minimum_churn_probability=0.7,
        database=database,
        max_tool_calls=4,
        planner=deterministic_planner,
    )

    observations = {
        item["result"]["contract"]: item["result"] for item in result["observations"]
    }

    checks = {
        "Completed tool calls": result["tool_calls"] == 2,
        "Monthly customer count": (
            observations["Month-to-month"]["customer_count"] == 2
        ),
        "Annual customer count": (observations["One year"]["customer_count"] == 1),
        "Monthly contract in report": ("Month-to-month" in result["answer"]),
        "Annual contract in report": ("One year" in result["answer"]),
    }

    for name, passed in checks.items():
        if not passed:
            raise SystemExit(f"Comparison verification failed: {name}")

        print(f"PASS: {name}")

    print("Comparison tools and computed report verified.")


if __name__ == "__main__":
    main()
