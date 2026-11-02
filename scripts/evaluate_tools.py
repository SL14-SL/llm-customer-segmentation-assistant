"""Evaluate tool decisions and save model responses for inspection."""

import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from customer_segmentation_assistant.tool_llm import generate_tool_decision


def main() -> int:
    """Check decision types and arguments, flagging clarification review."""
    cases = json.loads(
        Path("evaluation/tool_cases.json").read_text(encoding="utf-8")
    )
    results = []

    for case in cases:
        print(f"\n--- {case['id']} ---", flush=True)
        print(case["question"], flush=True)
        started = perf_counter()
        record = {
            "id": case["id"],
            "question": case["question"],
            "expected_kind": case["expected_kind"],
        }

        try:
            decision = generate_tool_decision(case["question"])
            record["decision"] = decision
            print(json.dumps(decision, indent=2), flush=True)

            if decision["kind"] != case["expected_kind"]:
                raise AssertionError("Unexpected decision kind.")

            if (
                case["expected_kind"] == "tool_call"
                and decision["arguments"] != case["expected_arguments"]
            ):
                raise AssertionError("Incorrect segment arguments.")

            record["automatic_pass"] = True
            print("Automatic checks: PASS", flush=True)

        except Exception as error:  # noqa: BLE001 - record each failed case
            record["automatic_pass"] = False
            record["error"] = f"{type(error).__name__}: {error}"
            print(f"FAIL: {record['error']}", flush=True)

        if "manual_review" in case:
            record["manual_review"] = case["manual_review"]
            record["manual_review_status"] = "pending"
            print(f"Manual review: {case['manual_review']}", flush=True)

        record["duration_seconds"] = round(perf_counter() - started, 2)
        results.append(record)

    output_dir = Path("data/evaluation")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    output = output_dir / f"tool-decisions-{timestamp}.json"
    output.write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    passed = sum(record["automatic_pass"] for record in results)
    print(f"\nAutomatic checks passed: {passed}/{len(results)}")
    print("Clarification quality requires the indicated manual review.")
    print(f"Responses saved: {output}")

    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())