"""Read customer segments from the local DuckDB database."""

from pathlib import Path

import duckdb
import pandas as pd

DEFAULT_DATABASE = Path("data/customers.duckdb")


def query_dataframe(
    sql: str,
    parameters: list[object] | None = None,
    *,
    database: Path = DEFAULT_DATABASE,
) -> pd.DataFrame:
    """Execute one SELECT query using a read-only database connection."""
    if not database.is_file():
        raise FileNotFoundError(f"Database not found: {database}")

    with duckdb.connect(str(database), read_only=True) as connection:
        statements = connection.extract_statements(sql)

        if len(statements) != 1:
            raise ValueError("Exactly one SQL statement is required.")

        if statements[0].type != duckdb.StatementType.SELECT:
            raise ValueError("Only SELECT statements are allowed.")

        return connection.execute(
            sql,
            parameters if parameters is not None else [],
        ).fetchdf()