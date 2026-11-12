"""Check the demo's public schema, reproducibility and file preservation."""

import re

import duckdb
import pytest

from customer_segmentation_assistant.database import query_dataframe
from customer_segmentation_assistant.prompts import SYSTEM_PROMPT
from customer_segmentation_assistant.text_sql_demo import create_text_sql_demo


def test_demo_supports_the_complete_prompt_schema(tmp_path):
    database = tmp_path / "demo.duckdb"
    create_text_sql_demo(database)
    with duckdb.connect(str(database), read_only=True) as connection:
        columns = {
            row[0] for row in connection.execute("DESCRIBE customers").fetchall()
        }
    prompt_columns = set(
        re.findall(r"^- (\w+): (?:VARCHAR|BIGINT|DOUBLE)", SYSTEM_PROMPT, re.MULTILINE)
    )
    assert columns == prompt_columns
    result = query_dataframe(
        "SELECT COUNT(*) AS n, COUNT(DISTINCT customerID) AS ids FROM customers",
        database=database,
    )
    assert result.iloc[0].tolist() == [300, 300]
    missing = query_dataframe(
        "SELECT COUNT(*) FROM customers WHERE TotalCharges IS NULL",
        database=database,
    )
    assert missing.iloc[0, 0] == 10
    groups = query_dataframe(
        "SELECT Contract, COUNT(*) FROM customers GROUP BY Contract",
        database=database,
    )
    assert set(groups.iloc[:, 1]) == {100}


def test_demo_is_reproducible_and_preserves_existing_files(tmp_path):
    first, second = tmp_path / "first.duckdb", tmp_path / "second.duckdb"
    create_text_sql_demo(first)
    create_text_sql_demo(second)
    query = "SELECT * FROM customers ORDER BY customerID"
    assert query_dataframe(query, database=first).equals(
        query_dataframe(query, database=second)
    )
    original = first.read_bytes()
    with pytest.raises(FileExistsError):
        create_text_sql_demo(first)
    assert first.read_bytes() == original
