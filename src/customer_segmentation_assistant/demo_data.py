"""Create a small synthetic database for segment-tool demonstrations."""

from pathlib import Path

import duckdb

DEMO_CUSTOMERS = [
    ("demo-001", "Month-to-month", 60.0, 0.80),
    ("demo-002", "Month-to-month", 90.0, 0.70),
    ("demo-003", "Month-to-month", 30.0, 0.20),
    ("demo-004", "One year", 50.0, 0.65),
    ("demo-005", "One year", 70.0, 0.85),
    ("demo-006", "Two year", 40.0, 0.10),
]


def create_demo_database(path: Path) -> None:
    """Create synthetic tool data without replacing an existing database."""
    if path.exists():
        raise FileExistsError(f"Database already exists: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(path)) as connection:
        connection.execute("""
            CREATE TABLE customers (
                customerID VARCHAR PRIMARY KEY,
                Contract VARCHAR NOT NULL,
                MonthlyCharges DOUBLE NOT NULL,
                churn_probability DOUBLE NOT NULL
            )
        """)
        connection.executemany(
            "INSERT INTO customers VALUES (?, ?, ?, ?)",
            DEMO_CUSTOMERS,
        )