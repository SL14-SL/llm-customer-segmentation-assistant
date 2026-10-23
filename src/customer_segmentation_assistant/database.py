"""Read customer segments from the local DuckDB database."""

from pathlib import Path

import duckdb
import pandas as pd

from customer_segmentation_assistant.sql_policy import validate_sql

DEFAULT_DATABASE = Path("data/customers.duckdb")


def query_dataframe(
    sql: str,
    parameters: list[object] | None = None,
    *,
    database: Path = DEFAULT_DATABASE,
) -> pd.DataFrame:
    """Execute one permitted query using a read-only connection."""
    if not database.is_file():
        raise FileNotFoundError(f"Database not found: {database}")

    validate_sql(sql)

    with duckdb.connect(str(database), read_only=True) as connection:
        return connection.execute(
            sql,
            parameters if parameters is not None else [],
        ).fetchdf()
