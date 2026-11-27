"""Read-only analytical tools with validated arguments."""

from pathlib import Path

from customer_segmentation_assistant.segments.criteria import (
    is_supported_contract,
    validate_probability,
)
from customer_segmentation_assistant.storage.database import (
    DEFAULT_DATABASE,
    query_dataframe,
)


def summarize_segment(
    *,
    contract: str,
    minimum_churn_probability: float,
    database: Path = DEFAULT_DATABASE,
) -> dict[str, int | float | str | None]:
    """Summarize customers matching a contract and inclusive risk threshold."""
    if not is_supported_contract(contract):
        raise ValueError("Unsupported contract type.")

    threshold = validate_probability(
        minimum_churn_probability,
        error_message=(
            "minimum_churn_probability must be a finite number from 0 to 1."
        ),
    )

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
