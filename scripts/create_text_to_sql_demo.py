"""Create reproducible synthetic data for the Text-to-SQL application."""

import argparse
import random
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb
import pandas as pd


def build_customers() -> pd.DataFrame:
    """Build synthetic records matching the documented customer schema."""
    rng = random.Random(42)
    rows = []

    for index in range(120):
        tenure = rng.randint(1, 72)
        monthly = round(rng.uniform(20, 120), 2)
        probability = round(rng.uniform(0, 1), 4)
        phone = rng.choice(["Yes", "No"])
        internet = rng.choice(["DSL", "Fiber optic", "No"])

        row = {
            "customerID": f"synthetic-{index + 1:04d}",
            "gender": rng.choice(["Female", "Male"]),
            "SeniorCitizen": rng.randint(0, 1),
            "Partner": rng.choice(["Yes", "No"]),
            "Dependents": rng.choice(["Yes", "No"]),
            "tenure": tenure,
            "PhoneService": phone,
            "MultipleLines": (
                rng.choice(["Yes", "No"])
                if phone == "Yes"
                else "No phone service"
            ),
            "InternetService": internet,
        }

        for column in (
            "OnlineSecurity",
            "OnlineBackup",
            "DeviceProtection",
            "TechSupport",
            "StreamingTV",
            "StreamingMovies",
        ):
            row[column] = (
                rng.choice(["Yes", "No"])
                if internet != "No"
                else "No internet service"
            )

        row.update({
            "Contract": ["Month-to-month", "One year", "Two year"][index % 3],
            "PaperlessBilling": rng.choice(["Yes", "No"]),
            "PaymentMethod": rng.choice([
                "Electronic check",
                "Mailed check",
                "Bank transfer (automatic)",
                "Credit card (automatic)",
            ]),
            "MonthlyCharges": monthly,
            "TotalCharges": (
                None if index % 12 == 0 else round(monthly * tenure, 2)
            ),
            "churn_probability": probability,
            "customer_value": (
                None if index % 15 == 0 else round(monthly * 12, 2)
            ),
            "action": rng.choice([
                "offer_discount",
                "send_email",
                "no_action",
            ]),
            "expected_value": round(rng.uniform(-20, 200), 2),
            "scored_at_utc": "2026-01-01T00:00:00Z",
            "model_name": "synthetic-demo-no-trained-model",
            "model_version": "synthetic",
            "model_run_id": "synthetic-run",
            "release_id": "synthetic-release",
        })
        rows.append(row)

    return pd.DataFrame(rows)


def main() -> None:
    """Create a demo database without replacing an existing file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data/text_to_sql_demo.duckdb"),
    )
    args = parser.parse_args()
    destination = args.database

    if destination.exists():
        parser.error(f"Database already exists: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    customers = build_customers()

    with TemporaryDirectory(dir=destination.parent) as temporary:
        temporary_database = Path(temporary) / "customers.duckdb"
        with duckdb.connect(str(temporary_database)) as connection:
            connection.register("synthetic_customers", customers)
            connection.execute(
                "CREATE TABLE customers AS SELECT * FROM synthetic_customers"
            )

        # Publish the completed database without overwriting an existing file.
        destination.hardlink_to(temporary_database)

    print(f"Created {destination} with {len(customers)} synthetic customers.")
    print("Scores, actions and values are artificial demonstration inputs.")


if __name__ == "__main__":
    main()
