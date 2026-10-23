"""Ask customer segmentation questions from the terminal."""

import argparse

from customer_segmentation_assistant.database import query_dataframe
from customer_segmentation_assistant.decisions import ClarificationDecision
from customer_segmentation_assistant.llm import DEFAULT_MODEL, generate_decision

MAX_CLARIFICATIONS = 3


def main() -> None:
    """Resolve clarifications and execute a permitted customer query."""
    parser = argparse.ArgumentParser(
        description="Ask an English customer segmentation question."
    )
    parser.add_argument("question")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    question = args.question.strip()
    if not question:
        parser.error("Question must not be empty.")

    context = [f"Original customer question: {question}"]

    for attempt in range(MAX_CLARIFICATIONS + 1):
        print("Generating decision...", flush=True)
        current_request = "\n\n".join(context)
        current_request += (
            "\n\nResolve the current request using all customer answers above. "
            "Generate SQL if the missing information has been supplied."
        )

        decision = generate_decision(
            current_request,
            model=args.model,
        )

        if not isinstance(decision, ClarificationDecision):
            print(f"\nSQL:\n{decision.sql}")
            result = query_dataframe(decision.sql)

            print(f"\nResult ({len(result)} rows):")
            if result.empty:
                print("No matching customers.")
            else:
                print(result.to_string(index=False))
            return

        print(f"\nClarification: {decision.question}")

        if attempt == MAX_CLARIFICATIONS:
            print("Clarification limit reached. Please ask a more specific question.")
            return

        try:
            answer = input("Your answer (Enter to cancel): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return

        if not answer:
            print("Cancelled.")
            return

        context.extend([
            f"Assistant clarification: {decision.question}",
            f"Customer answer: {answer}",
        ])


if __name__ == "__main__":
    main()