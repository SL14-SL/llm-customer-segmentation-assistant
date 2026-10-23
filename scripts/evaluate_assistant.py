"""Evaluate local assistant decisions against reference cases."""

import json
from pathlib import Path
from time import perf_counter

from pandas.testing import assert_frame_equal

from customer_segmentation_assistant.database import query_dataframe
from customer_segmentation_assistant.decisions import (
    ClarificationDecision,
    QueryDecision,
)
from customer_segmentation_assistant.llm import generate_decision


def main() -> None:
    """Run reference questions and report individual outcomes."""
    cases = json.loads(
        Path("evaluation/cases.json").read_text(encoding="utf-8")
    )
    passed = 0

    for case in cases:
        print(f"\n--- {case['id']} ---", flush=True)
        started = perf_counter()

        try:
            decision = generate_decision(case["question"])

            if "clarification_answer" in case:
                if not isinstance(decision, ClarificationDecision):
                    raise AssertionError(
                        "Expected a clarification before the follow-up answer."
                    )

                print(f"Initial clarification: {decision.question}")

                context = [
                    f"Original customer question: {case['question']}",
                    f"Assistant clarification: {decision.question}",
                    f"Customer answer: {case['clarification_answer']}",
                ]
                current_request = "\n\n".join(context)
                current_request += (
                    "\n\nResolve the current request using all customer answers "
                    "above. Generate SQL if the missing information has been "
                    "supplied."
                )

                decision = generate_decision(current_request)
                
            if case.get("expected_behavior") == "clarify":
                if not isinstance(decision, ClarificationDecision):
                    raise AssertionError("Expected a clarification.")

                print(f"Clarification: {decision.question}")
                print("Review manually whether it asks about the risk threshold.")
            else:
                if not isinstance(decision, QueryDecision):
                    raise AssertionError("Expected a SQL query.")

                expected = query_dataframe(case["expected_sql"])
                actual = query_dataframe(decision.sql)

                # Compare values by position, ignoring output aliases.
                actual.columns = range(len(actual.columns))
                expected.columns = range(len(expected.columns))

                if not case.get("order_matters", True):
                    actual = actual.sort_values(
                        by=list(actual.columns),
                        na_position="last",
                    ).reset_index(drop=True)
                    expected = expected.sort_values(
                        by=list(expected.columns),
                        na_position="last",
                    ).reset_index(drop=True)

                assert_frame_equal(
                    actual,
                    expected,
                    check_dtype=False,
                    check_exact=False,
                    rtol=1e-6,
                    atol=1e-9,
                )

                print(f"SQL: {decision.sql}")

            passed += 1
            print("PASS")

        except Exception as error:  # noqa: BLE001 - report each failed case
            print(f"FAIL: {type(error).__name__}: {error}")

        print(f"Duration: {perf_counter() - started:.1f} seconds")

    print(f"\nPassed: {passed}/{len(cases)}")
    raise SystemExit(0 if passed == len(cases) else 1)


if __name__ == "__main__":
    main()
