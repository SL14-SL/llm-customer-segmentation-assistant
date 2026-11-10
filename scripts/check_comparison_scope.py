"""Inspect scope classification separately from extraction and execution."""

import argparse
import json
from pathlib import Path

from customer_segmentation_assistant.comparison_scope import (
    check_comparison_scope,
)


def main() -> int:
    """Check scope detection against the current development cases."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen2.5-coder:3b")
    args = parser.parse_args()
    print(f"Model: {args.model}", flush=True)

    cases = json.loads(
        Path("evaluation/comparison_cases.json").read_text(encoding="utf-8")
    )
    passed = 0
    total = 0

    for case in cases:
        for index, message in enumerate(case["messages"]):
            total += 1
            print(f"\nUSER: {message}", flush=True)
            expected_unsupported = (
                case["expected_kind"] == "unsupported"
                and index == len(case["messages"]) - 1
            )

            try:
                requirements = check_comparison_scope(
                    message,
                    model=args.model,
                )
                correct = bool(requirements) == expected_unsupported
                print(
                    f"DETECTED: {json.dumps(requirements)}",
                    flush=True,
                )
            except Exception as error:  # noqa: BLE001 - report each case
                correct = False
                print(
                    f"ERROR: {type(error).__name__}: {error}",
                    flush=True,
                )

            passed += int(correct)
            print(f"Expected scope classification: {correct}", flush=True)

    print(f"\nScope checks passed: {passed}/{total}")
    print("Review whether reported capability violations match the request.")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())