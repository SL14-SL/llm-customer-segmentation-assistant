"""Verify that tool dispatch accepts only the intended call format."""

import json

import pytest

from customer_segmentation_assistant.demo_data import create_demo_database
from customer_segmentation_assistant.tool_dispatch import execute_tool_call


def valid_call():
    return {
        "tool": "summarize_segment",
        "arguments": {
            "contract": "One year",
            "minimum_churn_probability": 0.65,
        },
    }


def test_executes_supported_tool(tmp_path):
    database = tmp_path / "demo.duckdb"
    create_demo_database(database)

    result = execute_tool_call(
        json.dumps(valid_call()),
        database=database,
    )

    assert result["customer_count"] == 2
    assert result["average_monthly_charges"] == pytest.approx(60.0)


@pytest.mark.parametrize(
    "raw",
    [
        "not JSON",
        "[]",
        "{}",
        '{"tool": "delete_database", "arguments": {}}',
        '{"tool": "summarize_segment", "arguments": []}',
    ],
)
def test_rejects_invalid_calls_before_database_access(tmp_path, raw):
    database = tmp_path / "missing.duckdb"

    with pytest.raises(ValueError):
        execute_tool_call(raw, database=database)

    assert not database.exists()


@pytest.mark.parametrize(
    "extra_argument",
    ["database", "sql", "unexpected"],
)
def test_rejects_extra_arguments(tmp_path, extra_argument):
    call = valid_call()
    call["arguments"][extra_argument] = "untrusted value"

    with pytest.raises(ValueError, match="Unexpected or missing"):
        execute_tool_call(
            json.dumps(call),
            database=tmp_path / "missing.duckdb",
        )


def test_rejects_missing_threshold(tmp_path):
    call = valid_call()
    del call["arguments"]["minimum_churn_probability"]

    with pytest.raises(ValueError, match="Unexpected or missing"):
        execute_tool_call(
            json.dumps(call),
            database=tmp_path / "missing.duckdb",
        )


def test_rejects_invalid_argument_value(tmp_path):
    call = valid_call()
    call["arguments"]["minimum_churn_probability"] = 65

    with pytest.raises(ValueError, match="finite number"):
        execute_tool_call(
            json.dumps(call),
            database=tmp_path / "missing.duckdb",
        )