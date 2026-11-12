"""Build reproducible fictional Text-to-SQL data without an upstream model."""

import argparse
import random
from pathlib import Path

import duckdb
import pandas as pd


def create_text_sql_demo(path: Path) -> None:
    """Create 300 fictional customers; refuse to replace any existing file."""
    if path.exists():
        raise FileExistsError(f"Database already exists: {path}")
    rng = random.Random(42)
    rows = []
    for index in range(300):
        tenure = rng.randint(0, 72)
        monthly = round(rng.uniform(20, 120), 2)
        probability = round(rng.random(), 4)
        internet = rng.choice(["DSL", "Fiber optic", "No"])
        phone = rng.choice(["Yes", "No"])
        row = {
            "customerID": f"synthetic-{index + 1:04d}",
            "gender": rng.choice(["Female", "Male"]),
            "SeniorCitizen": rng.randint(0, 1),
            "Partner": rng.choice(["Yes", "No"]),
            "Dependents": rng.choice(["Yes", "No"]),
            "tenure": tenure,
            "PhoneService": phone,
            "MultipleLines": rng.choice(["Yes", "No"])
            if phone == "Yes"
            else "No phone service",
            "InternetService": internet,
            "Contract": ["Month-to-month", "One year", "Two year"][index % 3],
            "PaperlessBilling": rng.choice(["Yes", "No"]),
            "PaymentMethod": rng.choice(
                [
                    "Electronic check",
                    "Mailed check",
                    "Bank transfer (automatic)",
                    "Credit card (automatic)",
                ]
            ),
            "MonthlyCharges": monthly,
            "TotalCharges": None if index % 30 == 0 else round(monthly * tenure, 2),
            "churn_probability": probability,
            "customer_value": None if index % 25 == 0 else round(monthly * 12, 2),
            "action": ["offer_discount", "send_email", "no_action"][index % 3],
            "expected_value": round(rng.uniform(-20, 200), 2),
            "scored_at_utc": "2026-01-01T00:00:00Z",
            "model_name": "synthetic-demo-no-trained-model",
            "model_version": "demo-v1",
            "model_run_id": "synthetic-demo",
            "release_id": "synthetic-demo-v1",
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
                else ("No internet service")
            )
        rows.append(row)
    frame = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(path)) as connection:
        connection.register("demo_rows", frame)
        connection.execute("CREATE TABLE customers AS SELECT * FROM demo_rows")


def main() -> None:
    """Create the dedicated demo database, or reuse it on subsequent starts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database", type=Path, default=Path("data/text_sql_demo.duckdb")
    )
    args = parser.parse_args()
    if args.database.exists():
        print(f"Using existing database: {args.database}")
        return
    create_text_sql_demo(args.database)
    print(f"Created {args.database}: 300 fictional customers, seed 42.")


if __name__ == "__main__":
    main()
