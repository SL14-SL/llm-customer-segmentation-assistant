"""Maintain segment criteria across clarification turns."""

import json
from dataclasses import dataclass, field

from customer_segmentation_assistant.tool_llm import (
    parse_segment_criteria,
    parse_tool_decision,
)


@dataclass
class SegmentConversation:
    """Collect criteria for one segment request."""

    criteria: dict[str, object] = field(
        default_factory=lambda: {
            "contract": None,
            "minimum_churn_probability": None,
        }
    )

    def update(self, extracted: dict[str, object]) -> dict[str, object]:
        """Apply supplied values while retaining previously known criteria."""
        validated = parse_segment_criteria(json.dumps(extracted))
        merged = dict(self.criteria)

        for name, value in validated.items():
            if value is not None:
                merged[name] = value

        decision = parse_tool_decision(json.dumps(merged))
        self.criteria = merged
        return decision