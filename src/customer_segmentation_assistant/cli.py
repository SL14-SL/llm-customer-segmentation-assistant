"""Ask customer segmentation questions from the terminal."""

import argparse

from customer_segmentation_assistant.database import query_dataframe
from customer_segmentation_assistant.decisions import ClarificationDecision
from customer_segmentation_assistant.llm import DEFAULT_MODEL, generate_decision


def main() -> None:
    """Generate a decision and execute permitted customer queries."""
    parser = argparse.ArgumentParser(
        description="Ask an English customer segmentation question."
    )
    parser.add_argument("question")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    print("Generating decision...", flush=True)
    decision = generate_decision(args.question, model=args.model)

    if isinstance(decision, ClarificationDecision):
        print(f"\nClarification: {decision.question}")
        return

    print(f"\nSQL:\n{decision.sql}")
    result = query_dataframe(decision.sql)

    print(f"\nResult ({len(result)} rows):")
    if result.empty:
        print("No matching customers.")
    else:
        print(result.to_string(index=False))


if __name__ == "__main__":
    main()
