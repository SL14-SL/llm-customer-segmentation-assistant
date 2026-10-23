"""Verify supported reference queries and rejected SQL."""

import json
from pathlib import Path

import pytest

from customer_segmentation_assistant.sql_policy import validate_sql

CASES_PATH = Path(__file__).resolve().parents[1] / "evaluation/cases.json"
REFERENCE_CASES = json.loads(CASES_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "case",
    [case for case in REFERENCE_CASES if "expected_sql" in case],
    ids=lambda case: case["id"],
)
def test_accepts_reference_queries(case):
    validate_sql(case["expected_sql"])


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM other",
        "SELECT * FROM information_schema.tables",
        "SELECT * FROM main.customers",
        "SELECT * FROM read_csv_auto('/tmp/customers.csv')",
        "SELECT * FROM 'data/customer_segmentation.parquet'",
        "SELECT getenv('HOME') FROM customers",
        "SELECT * FROM customers; DROP TABLE customers",
        "SELECT * FROM customers JOIN customers AS other ON TRUE",
        "WITH x AS (SELECT * FROM customers) SELECT * FROM x",
        "SELECT (SELECT COUNT(*) FROM customers) FROM customers",
    ],
)
def test_rejects_unsupported_queries(sql):
    with pytest.raises(ValueError):
        validate_sql(sql)
