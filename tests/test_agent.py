"""Verify agent execution and boundaries independently of model quality."""

import pytest

from customer_segmentation_assistant.agent import next_action_schema, run_comparison
from customer_segmentation_assistant.demo_data import create_demo_database


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "agent.duckdb"
    create_demo_database(path)
    return path


def run_with_actions(database, actions, *, max_tool_calls=4):
    iterator = iter(actions)
    return run_comparison(
        contracts=("Month-to-month", "One year"),
        minimum_churn_probability=0.7,
        database=database,
        max_tool_calls=max_tool_calls,
        planner=lambda context: next(iterator),
    )


def test_planner_receives_computed_results(database):
    contexts = []

    def planner(context):
        contexts.append(context)
        count = len(context["observations"])

        if count == 0:
            return {"kind": "tool_call", "contract": "Month-to-month"}
        if count == 1:
            return {"kind": "tool_call", "contract": "One year"}
        return {"kind": "finish"}

    result = run_comparison(
        contracts=("Month-to-month", "One year"),
        minimum_churn_probability=0.7,
        database=database,
        planner=planner,
    )

    assert result["tool_calls"] == 2
    assert contexts[0]["observations"] == []
    assert contexts[1]["observations"][0]["result"]["customer_count"] == 2
    assert contexts[2]["observations"][1]["result"]["customer_count"] == 1
    assert contexts[0]["remaining_contracts"] == [
        "Month-to-month",
        "One year",
    ]
    assert contexts[1]["remaining_contracts"] == ["One year"]
    assert contexts[2]["remaining_contracts"] == []
    assert all(
        observation["call"]["arguments"]["minimum_churn_probability"] == 0.7
        for observation in result["observations"]
    )


def test_rejects_early_finish(database):
    with pytest.raises(ValueError, match="before comparing"):
        run_with_actions(
            database,
            [{"kind": "finish"}],
        )


def test_rejects_contract_outside_scope(database):
    with pytest.raises(ValueError, match="outside the scope"):
        run_with_actions(
            database,
            [{"kind": "tool_call", "contract": "Two year"}],
        )


def test_rejects_duplicate_call(database):
    with pytest.raises(ValueError, match="completed segment again"):
        run_with_actions(
            database,
            [
                {"kind": "tool_call", "contract": "One year"},
                {"kind": "tool_call", "contract": "One year"},
            ],
        )


def test_enforces_tool_call_limit(database):
    with pytest.raises(RuntimeError, match="tool-call limit"):
        run_with_actions(
            database,
            [
                {"kind": "tool_call", "contract": "One year"},
                {"kind": "tool_call", "contract": "Month-to-month"},
            ],
            max_tool_calls=1,
        )


def test_action_schema_requires_missing_segment():
    remaining = ["Month-to-month"]
    schema = next_action_schema(remaining)

    assert schema["properties"]["kind"]["enum"] == ["tool_call"]
    assert schema["properties"]["contract"]["enum"] == ["Month-to-month"]
    assert "answer" not in schema["properties"]

    remaining.append("One year")
    assert schema["properties"]["contract"]["enum"] == ["Month-to-month"]


def test_action_schema_allows_finish_only_after_completion():
    schema = next_action_schema([])

    assert schema["properties"]["kind"]["enum"] == ["finish"]
    assert schema["required"] == ["kind"]
    assert "answer" not in schema["properties"]
    assert "contract" not in schema["properties"]