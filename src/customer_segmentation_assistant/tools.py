"""Read-only analytical tools with validated arguments."""

import math
from pathlib import Path

from customer_segmentation_assistant.database import (
    DEFAULT_DATABASE,
    query_dataframe,
)

CONTRACT_TYPES = frozenset({
    "Month-to-month",
    "One year",
    "Two year",
})


def summarize_segment(
    *,
    contract: str,
    minimum_churn_probability: float,
    database: Path = DEFAULT_DATABASE,
) -> dict[str, int | float | str | None]:
    """Summarize customers matching a contract and inclusive risk threshold."""
    if not isinstance(contract, str) or contract not in CONTRACT_TYPES:
        raise ValueError("Unsupported contract type.")

    if (
        isinstance(minimum_churn_probability, bool)
        or not isinstance(minimum_churn_probability, (int, float))
        or not math.isfinite(minimum_churn_probability)
        or not 0 <= minimum_churn_probability <= 1
    ):
        raise ValueError(
            "minimum_churn_probability must be a finite number from 0 to 1."
        )

    threshold = float(minimum_churn_probability)

    result = query_dataframe(
        """
        SELECT
            COUNT(*) AS customer_count,
            AVG(MonthlyCharges) AS average_monthly_charges,
            AVG(churn_probability) AS average_churn_probability
        FROM customers
        WHERE Contract = ?
          AND churn_probability >= ?
        """,
        [contract, threshold],
        database=database,
    )
    row = result.iloc[0]
    count = int(row["customer_count"])

    return {
        "contract": contract,
        "minimum_churn_probability": threshold,
        "customer_count": count,
        "average_monthly_charges": (
            float(row["average_monthly_charges"]) if count else None
        ),
        "average_churn_probability": (
            float(row["average_churn_probability"]) if count else None
        ),
    }