"""Verify the bounded comparison interface without live model inference."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from customer_segmentation_assistant.comparison import agent, request
from customer_segmentation_assistant.llm.exceptions import (
    OllamaConnectionError,
    OllamaTimeoutError,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
APP_PATH = PROJECT_ROOT / "streamlit_agent_demo.py"

COMPLETE_QUESTION = (
    "Compare monthly and annual contracts with churn probability at least 70%."
)


def extracted_criteria(contracts, probabilities, requirements=None):
    """Create a representative structured extraction response."""
    return json.dumps(
        {
            "contracts": contracts,
            "minimum_probabilities": probabilities,
            "unsupported_requirements": (
                requirements if requirements is not None else []
            ),
        }
    )


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Start the comparison interface with isolated application data."""
    monkeypatch.chdir(tmp_path)

    extraction_model = Mock(
        side_effect=AssertionError("Unexpected extraction request.")
    )

    planner_model = Mock(side_effect=AssertionError("Unexpected planner request."))

    monkeypatch.setattr(
        request,
        "generate_structured_response",
        extraction_model,
    )

    monkeypatch.setattr(
        agent,
        "generate_structured_response",
        planner_model,
    )

    application = AppTest.from_file(
        str(APP_PATH),
        default_timeout=15,
    ).run()

    assert not application.exception

    return application, extraction_model, planner_model


def submit_question(application, question):
    """Submit a comparison request and complete the resulting rerun."""
    application.chat_input[0].set_value(question).run()

    assert not application.exception


def last_reply(application):
    """Return the latest rendered assistant message."""
    return application.chat_message[-1].markdown[0].value


def execution_buttons(application):
    """Find buttons that allow comparison execution."""
    return [
        button for button in application.button if button.label == "Run this comparison"
    ]


def prepare_complete_comparison(application, extraction_model):
    """Extract complete criteria without executing the comparison."""
    extraction_model.side_effect = None

    extraction_model.return_value = extracted_criteria(
        ["Month-to-month", "One year"],
        [0.7],
    )

    submit_question(application, COMPLETE_QUESTION)


def test_application_starts(app):
    application, extraction_model, planner_model = app

    assert any(
        title.value == "Customer Segment Comparison" for title in application.title
    )

    assert len(application.chat_input) == 1

    assert application.session_state["decision"] is None
    assert application.session_state["result"] is None
    assert not execution_buttons(application)

    extraction_model.assert_not_called()
    planner_model.assert_not_called()


def test_complete_criteria_require_explicit_confirmation(app):
    application, extraction_model, planner_model = app

    prepare_complete_comparison(application, extraction_model)

    assert "The comparison criteria are complete." in last_reply(application)

    assert application.session_state["decision"] == {
        "kind": "comparison",
        "arguments": {
            "contracts": ["Month-to-month", "One year"],
            "minimum_churn_probability": 0.7,
        },
    }

    assert len(execution_buttons(application)) == 1

    assert any(item.value == "Recognized filters" for item in application.subheader)

    assert application.session_state["result"] is None
    assert not Path("data/agent_demo.duckdb").exists()

    planner_model.assert_not_called()


def test_clarification_preserves_selected_contracts(app):
    application, extraction_model, planner_model = app

    extraction_model.side_effect = [
        extracted_criteria(
            ["Month-to-month", "One year"],
            [],
        ),
        extracted_criteria(
            [],
            [0.7],
        ),
    ]

    submit_question(
        application,
        "Compare monthly and annual contracts.",
    )

    assert last_reply(application) == "Which minimum churn probability should I use?"

    assert not execution_buttons(application)

    submit_question(application, "At least 70%.")

    assert application.session_state["decision"] == {
        "kind": "comparison",
        "arguments": {
            "contracts": ["Month-to-month", "One year"],
            "minimum_churn_probability": 0.7,
        },
    }

    assert len(execution_buttons(application)) == 1

    second_prompt = extraction_model.call_args_list[1].kwargs["prompt"]

    assert "Already selected contracts" in second_prompt
    assert "At least 70%." in second_prompt

    planner_model.assert_not_called()


def test_scope_guard_displays_unsupported_message(app):
    application, extraction_model, planner_model = app

    submit_question(
        application,
        (
            "Compare monthly and annual contracts "
            "with churn probability at least 60%, "
            "but only customers with tenure of at least 24 months."
        ),
    )

    assert "Unsupported requirements" in last_reply(application)
    assert "tenure" in last_reply(application).lower()

    assert application.session_state["decision"]["kind"] == "unsupported"
    assert application.session_state["result"] is None

    assert not execution_buttons(application)
    assert not Path("data/agent_demo.duckdb").exists()

    extraction_model.assert_not_called()
    planner_model.assert_not_called()


def test_model_detected_unsupported_requirements(app):
    application, extraction_model, planner_model = app

    extraction_model.side_effect = None

    extraction_model.return_value = extracted_criteria(
        ["Month-to-month", "One year"],
        [0.7],
        ["Additional unsupported analytical requirement"],
    )

    submit_question(application, COMPLETE_QUESTION)

    assert "Additional unsupported analytical requirement" in last_reply(application)

    assert application.session_state["decision"]["kind"] == "unsupported"
    assert not execution_buttons(application)

    extraction_model.assert_called_once()
    planner_model.assert_not_called()


def test_confirmed_comparison_executes_real_tools(app):
    application, extraction_model, planner_model = app

    prepare_complete_comparison(application, extraction_model)

    planner_model.side_effect = [
        json.dumps(
            {
                "kind": "tool_call",
                "contract": "Month-to-month",
            }
        ),
        json.dumps(
            {
                "kind": "tool_call",
                "contract": "One year",
            }
        ),
        json.dumps({"kind": "finish"}),
    ]

    execution_buttons(application)[0].click().run()

    assert not application.exception
    assert not application.error

    result = application.session_state["result"]

    assert result is not None
    assert result["tool_calls"] == 2

    observations = {
        item["result"]["contract"]: item["result"] for item in result["observations"]
    }

    monthly = observations["Month-to-month"]
    annual = observations["One year"]

    assert monthly["customer_count"] == 2
    assert monthly["average_monthly_charges"] == pytest.approx(75.0)
    assert monthly["average_churn_probability"] == pytest.approx(0.75)

    assert annual["customer_count"] == 1
    assert annual["average_monthly_charges"] == pytest.approx(70.0)
    assert annual["average_churn_probability"] == pytest.approx(0.85)

    assert any(item.value == "Computed report" for item in application.subheader)

    assert any(
        "Month-to-month" in item.value and "One year" in item.value
        for item in application.text
    )

    assert len(application.session_state["actions"]) == 3

    assert Path("data/agent_demo.duckdb").is_file()
    assert planner_model.call_count == 3


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            OllamaTimeoutError("Technical timeout"),
            "The model request timed out.",
        ),
        (
            OllamaConnectionError("Connection refused"),
            "Could not connect to Ollama.",
        ),
    ],
)
def test_displays_actionable_extraction_errors(app, error, expected):
    application, extraction_model, planner_model = app

    extraction_model.side_effect = error

    submit_question(application, COMPLETE_QUESTION)

    assert expected in last_reply(application)
    assert application.session_state["decision"] is None
    assert application.session_state["result"] is None

    assert not execution_buttons(application)

    planner_model.assert_not_called()


def test_failed_request_invalidates_previous_confirmation(app):
    application, extraction_model, planner_model = app

    prepare_complete_comparison(application, extraction_model)

    assert len(execution_buttons(application)) == 1

    extraction_model.side_effect = OllamaTimeoutError("Technical timeout")

    submit_question(
        application,
        "Use a minimum churn probability of 80%.",
    )

    assert "The model request timed out." in last_reply(application)

    assert application.session_state["decision"] is None
    assert application.session_state["result"] is None

    assert not execution_buttons(application)

    planner_model.assert_not_called()


def test_displays_planner_timeout(app):
    application, extraction_model, planner_model = app

    prepare_complete_comparison(application, extraction_model)

    planner_model.side_effect = [
        json.dumps(
            {
                "kind": "tool_call",
                "contract": "Month-to-month",
            }
        ),
        OllamaTimeoutError("Planner timed out"),
    ]

    execution_buttons(application)[0].click().run()

    assert not application.exception

    assert any(
        "The model request timed out." in item.value for item in application.error
    )

    assert application.session_state["result"] is None

    assert len(application.session_state["actions"]) == 1
    assert planner_model.call_count == 2

    assert not any(item.value == "Computed report" for item in application.subheader)


def test_resets_comparison(app):
    application, extraction_model, planner_model = app

    prepare_complete_comparison(application, extraction_model)

    assert application.session_state["messages"]
    assert len(execution_buttons(application)) == 1

    reset_button = next(
        button
        for button in application.sidebar.button
        if button.label == "New comparison"
    )

    reset_button.click().run()

    assert not application.exception

    assert not application.session_state["messages"]
    assert not application.session_state["actions"]
    assert application.session_state["decision"] is None
    assert application.session_state["result"] is None

    assert application.session_state["comparison"].criteria == {
        "contracts": [],
        "minimum_churn_probability": None,
    }

    assert not execution_buttons(application)

    extraction_model.assert_called_once()
    planner_model.assert_not_called()
