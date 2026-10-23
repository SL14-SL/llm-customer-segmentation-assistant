"""Verify the query contract against an isolated test database."""

import duckdb
import pytest

from customer_segmentation_assistant.database import query_dataframe


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "customers.duckdb"

    with duckdb.connect(str(path)) as connection:
        connection.execute("""
            CREATE TABLE customers (
                customerID VARCHAR,
                churn_probability DOUBLE
            )
        """)
        connection.execute("""
            INSERT INTO customers VALUES
                ('customer-a', 0.2),
                ('customer-b', 0.8)
        """)

    return path


def test_parameterized_segment_query(database):
    result = query_dataframe(
        """
        SELECT customerID
        FROM customers
        WHERE churn_probability >= ?
        ORDER BY customerID
        """,
        [0.5],
        database=database,
    )

    assert result["customerID"].tolist() == ["customer-b"]


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM customers",
        "DROP TABLE customers",
        "CREATE TABLE other (id INTEGER)",
        "UPDATE customers SET churn_probability = 0",
    ],
)
def test_rejects_write_statements(database, sql):
    with pytest.raises(ValueError, match="Only SELECT"):
        query_dataframe(sql, database=database)

    result = query_dataframe(
        "SELECT COUNT(*) AS total FROM customers",
        database=database,
    )
    assert result["total"].item() == 2


def test_rejects_multiple_statements(database):
    with pytest.raises(ValueError, match="Exactly one"):
        query_dataframe(
            "SELECT * FROM customers; SELECT 1",
            database=database,
        )


def test_rejects_empty_query(database):
    with pytest.raises(ValueError, match="Exactly one"):
        query_dataframe("", database=database)


def test_missing_database_does_not_create_file(tmp_path):
    path = tmp_path / "missing.duckdb"

    with pytest.raises(FileNotFoundError):
        query_dataframe("SELECT 1", database=path)

    assert not path.exists()
