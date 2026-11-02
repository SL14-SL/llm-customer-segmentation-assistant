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

    def update(self, extracted: dict[str, object]) -> dict[str, object]:
        """Validate an update and retain criteria absent from that turn."""
        # JSON round-trip also detaches mutable lists from the caller.
        supplied = json.loads(json.dumps(extracted))
        parse_comparison_request(json.dumps(supplied))
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