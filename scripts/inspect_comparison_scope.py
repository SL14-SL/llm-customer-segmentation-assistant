"""Inspect raw scope extraction for one supported and one unsupported request."""

from customer_segmentation_assistant.comparison_scope import (
    check_comparison_scope,
)


def main() -> None:
    questions = [
        (
            "Compare monthly and annual contracts "
            "with predicted churn probability of at least 60%."
        ),
        (
            "Compare monthly and annual contracts "
            "with predicted churn probability of at least 60%, "
            "but only customers with tenure of at least 24 months."
        ),
    ]

    for model in ("qwen2.5-coder:3b", "llama3:latest"):
        print(f"\nMODEL: {model}", flush=True)

        for question in questions:
            print(f"\nUSER: {question}", flush=True)

            try:
                result = check_comparison_scope(question, model=model)
                print(f"POLICY RESULT: {result}", flush=True)
            except ValueError as error:
                print(f"VALIDATION ERROR: {error}", flush=True)


if __name__ == "__main__":
    main()