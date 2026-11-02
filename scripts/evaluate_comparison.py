"""Evaluate comparison interpretation, dialogue and real tool execution."""

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from customer_segmentation_assistant.agent import (
    propose_next_action,
    run_comparison,
)
from customer_segmentation_assistant.comparison_conversation import (
    ComparisonConversation,
)
from customer_segmentation_assistant.comparison_request import (
    extract_comparison_follow_up,
)
from customer_segmentation_assistant.demo_data import create_demo_database
from customer_segmentation_assistant.llm import DEFAULT_MODEL


def require(condition: bool, message: str) -> None:
    """Raise a visible evaluation failure."""
    if not condition:
        raise AssertionError(message)


def evaluate_case(case, database, record):
    """Evaluate one independent conversation against supplied expectations."""
    conversation = ComparisonConversation()

    for index, message in enumerate(case["messages"]):
        extracted = extract_comparison_follow_up(
            message,
            current_criteria=conversation.criteria,
            model=DEFAULT_MODEL,
        )
        decision = conversation.update(extracted)
        record["turns"].append({
            "message": message,
            "extracted": extracted,
            "decision": decision,
        })

        if index < len(case["messages"]) - 1:
            require(
                decision["kind"] == "clarification",
                "Expected a clarification before the follow-up.",
            )

    require(
        decision["kind"] == case["expected_kind"],
        f"Expected {case['expected_kind']}, received {decision['kind']}.",
    )

    if case["expected_kind"] != "comparison":
        return

    arguments = decision["arguments"]
    require(
        set(arguments["contracts"]) == set(case["expected_contracts"]),
        "Incorrect contract selection.",
    )
    require(
        math.isclose(
            arguments["minimum_churn_probability"],
            case["expected_threshold"],
            rel_tol=0,
            abs_tol=1e-9,
        ),
        "Incorrect probability threshold.",
    )

    def planner(context):
        action = propose_next_action(context, model=DEFAULT_MODEL)
        record["actions"].append(action)
        return action

    result = run_comparison(
        contracts=tuple(arguments["contracts"]),
        minimum_churn_probability=arguments["minimum_churn_probability"],
        database=database,
        planner=planner,
    )
    record["result"] = result

    observed = {
        item["result"]["contract"]: item["result"]
        for item in result["observations"]
    }
    require(
        set(observed) == set(case["expected_metrics"]),
        "Incorrect result coverage.",
    )
    require(
        result["tool_calls"] == len(case["expected_contracts"]),
        "Unexpected number of tool calls.",
    )

    for contract, expected in case["expected_metrics"].items():
        actual = observed[contract]

        for field, value in expected.items():
            if value is None:
                require(
                    actual[field] is None,
                    f"{contract}: expected no value for {field}.",
                )
            else:
                require(
                    actual[field] is not None
                    and math.isclose(
                        actual[field],
                        value,
                        rel_tol=1e-9,
                        abs_tol=1e-9,
                    ),
                    f"{contract}: incorrect {field}.",
                )


def main() -> int:
    """Run new cases on a fresh synthetic database and save all outcomes."""
    cases = json.loads(
        Path("evaluation/comparison_cases.json").read_text(encoding="utf-8")
    )
    records = []

    with TemporaryDirectory() as directory:
        database = Path(directory) / "evaluation.duckdb"
        create_demo_database(database)

        for case in cases:
            print(f"\n--- {case['id']} ---", flush=True)
            started = perf_counter()
            record = {
                "id": case["id"],
                "turns": [],
                "actions": [],
            }

            try:
                evaluate_case(case, database, record)
                record["passed"] = True
                print("PASS", flush=True)
            except Exception as error:  # noqa: BLE001 - record each failed case
                record["passed"] = False
                record["error"] = f"{type(error).__name__}: {error}"
                print(f"FAIL: {record['error']}", flush=True)

            record["duration_seconds"] = round(perf_counter() - started, 2)
            records.append(record)

    passed = sum(record["passed"] for record in records)
    output_dir = Path("data/evaluation")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    output = output_dir / f"comparison-{timestamp}.json"
    output.write_text(
        json.dumps(
            {"model": DEFAULT_MODEL, "cases": records},
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    print(f"\nEnd-to-end cases passed: {passed}/{len(records)}")
    print(f"Full dialogue, actions and results saved: {output}")
    return 0 if passed == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())