"""Check a comparison clarification dialogue using the local model."""

import json

from customer_segmentation_assistant.comparison_conversation import (
    ComparisonConversation,
)
from customer_segmentation_assistant.comparison_request import (
    extract_comparison_follow_up,
)


def main() -> None:
    """Verify that a threshold reply preserves the requested contracts."""
    conversation = ComparisonConversation()

    for message in [
        "Compare monthly and annual contracts.",
        "Use a minimum churn probability of 70%.",
    ]:
        print(f"\nUSER: {message}", flush=True)

        extracted = extract_comparison_follow_up(
            message,
            current_criteria=conversation.criteria,
        )
        print(f"EXTRACTED: {json.dumps(extracted)}", flush=True)

        decision = conversation.update(extracted)
        print(f"DECISION: {json.dumps(decision)}", flush=True)

    assert decision["kind"] == "comparison"
    assert set(decision["arguments"]["contracts"]) == {
        "Month-to-month",
        "One year",
    }
    assert decision["arguments"]["minimum_churn_probability"] == 0.7

    print("\nComparison clarification state: OK")


if __name__ == "__main__":
    main()