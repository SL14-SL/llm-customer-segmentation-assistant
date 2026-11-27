"""Shared validation of customer segment criteria."""

import json
import math

CONTRACT_TYPES = frozenset(
    {
        "Month-to-month",
        "One year",
        "Two year",
    }
)


def is_supported_contract(value: object) -> bool:
    """Check whether a value identifies a supported contract."""
    return isinstance(value, str) and value in CONTRACT_TYPES


def validate_probability(
    value: object,
    *,
    error_message: str = ("Minimum probability must be a finite number from 0 to 1."),
) -> float:
    """Validate a probability without changing its numerical precision."""
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not 0 <= value <= 1
        or not math.isfinite(value)
    ):
        raise ValueError(error_message)

    return float(value)


def normalize_probability(value: object) -> float:
    """Validate and normalize a model-generated probability."""
    return round(validate_probability(value), 12)


def parse_segment_criteria(raw: str) -> dict[str, object]:
    """Validate extracted criteria without accessing customer data."""
    try:
        criteria = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("Criteria must be valid JSON.") from error

    if not isinstance(criteria, dict):
        raise ValueError(  # noqa: TRY004
            "Criteria must be a JSON object."
        )

    if set(criteria) != {"contract", "minimum_churn_probability"}:
        raise ValueError("Unexpected or missing criteria fields.")

    contract = criteria["contract"]

    if contract is not None and not is_supported_contract(contract):
        raise ValueError("Unsupported contract type.")

    threshold = criteria["minimum_churn_probability"]

    if threshold is not None:
        threshold = normalize_probability(threshold)

    return {
        "contract": contract,
        "minimum_churn_probability": threshold,
    }
