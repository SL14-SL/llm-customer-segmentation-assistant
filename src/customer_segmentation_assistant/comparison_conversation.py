"""Preserve comparison criteria across clarification turns."""

import json
from dataclasses import dataclass, field

from customer_segmentation_assistant.comparison_request import (
    parse_comparison_request,
)


@dataclass
class ComparisonConversation:
    """Collect criteria for one comparison request."""

    criteria: dict[str, object] = field(
        default_factory=lambda: {
            "contracts": [],
            "minimum_churn_probability": None,
        }
    )
    unsupported_message: str | None = None

    def update(self, extracted: dict[str, object]) -> dict[str, object]:
        """Validate updates and retain unsupported requirements."""
        if self.unsupported_message is not None:
            return {
                "kind": "unsupported",
                "message": self.unsupported_message,
            }

        supplied = json.loads(json.dumps(extracted))
        supplied_decision = parse_comparison_request(json.dumps(supplied))

        if supplied_decision["kind"] == "unsupported":
            self.unsupported_message = supplied_decision["message"]
            return supplied_decision

        merged = json.loads(json.dumps(self.criteria))

        if supplied["contracts"]:
            merged["contracts"] = supplied["contracts"]

        if supplied["minimum_churn_probability"] is not None:
            merged["minimum_churn_probability"] = (
                supplied["minimum_churn_probability"]
            )

        decision = parse_comparison_request(json.dumps(merged))
        self.criteria = merged
        return decision