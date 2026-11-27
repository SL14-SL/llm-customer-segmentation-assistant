"""Verify the Text-to-SQL interface without live model inference."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from customer_segmentation_assistant.demo.text_to_sql import (
    create_text_sql_demo,
)
from customer_segmentation_assistant.llm.exceptions import (
    OllamaConnectionError,
    OllamaTimeoutError,
)
from customer_segmentation_assistant.storage import database
from customer_segmentation_assistant.text_to_sql import assistant

PROJECT_ROOT = Path(__file__).resolve().parents[3]
APP_PATH = PROJECT_ROOT / "streamlit_app.py"


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Start the interface with an isolated synthetic database."""
    database_path = tmp_path / "customers.duckdb"

    create_text_sql_demo(database_path)

    original_query = database.query_dataframe

    def query_test_database(sql, *args, **kwargs):
        kwargs["database"] = database_path
        return original_query(sql, *args, **kwargs)

    monkeypatch.setattr(
        database,
        "DEFAULT_DATABASE",
        database_path,
    )
    monkeypatch.setattr(
        database,
        "query_dataframe",
        query_test_database,
    )
    monkeypatch.setenv("SYNTHETIC_DEMO", "1")

    model = Mock(side_effect=AssertionError("Unexpected model request."))

    monkeypatch.setattr(
        assistant,
        "generate_structured_response",
        model,
    )

    application = AppTest.from_file(
        str(APP_PATH),
        default_timeout=15,
    ).run()

    assert not application.exception

    return application, model


def submit_question(application, question):
    """Submit a chat message and complete the resulting rerun."""
    application.chat_input[0].set_value(question).run()

    assert not application.exception


def last_reply(application):
    """Return the latest rendered assistant message."""
    return application.chat_message[-1].markdown[0].value


def test_application_starts(app):
    application, model = app

    assert any(
        title.value == "Customer Segmentation Assistant" for title in application.title
    )

    assert len(application.chat_input) == 1

    assert any(
        "Synthetic demo: 300 fictional customers" in item.value
        for item in application.info
    )

    model.assert_not_called()


def test_successful_query(app):
    application, model = app

    model.side_effect = None
    model.return_value = json.dumps(
        {
            "kind": "query",
            "sql": "SELECT COUNT(*) AS customer_count FROM customers",
        }
    )

    submit_question(
        application,
        "How many customers are in the dataset?",
    )

    assert last_reply(application) == "Your query returned 1 row."

    assert len(application.dataframe) == 1
    assert application.dataframe[0].value.iloc[0, 0] == 300

    assert not application.session_state["pending_context"]
    assert application.session_state["clarification_count"] == 0

    model.assert_called_once()


def test_clarification_and_follow_up(app):
    application, model = app

    model.side_effect = [
        json.dumps(
            {
                "kind": "clarification",
                "question": "Which minimum churn probability should I use?",
            }
        ),
        json.dumps(
            {
                "kind": "query",
                "sql": (
                    "SELECT COUNT(*) AS customer_count FROM customers "
                    "WHERE churn_probability >= 0.7"
                ),
            }
        ),
    ]

    submit_question(
        application,
        "How many customers are high risk?",
    )

    assert last_reply(application) == "Which minimum churn probability should I use?"

    assert application.session_state["clarification_count"] == 1
    assert application.session_state["pending_context"]
    assert len(application.dataframe) == 0

    submit_question(application, "At least 70%.")

    assert last_reply(application) == "Your query returned 1 row."
    assert len(application.dataframe) == 1

    assert application.session_state["clarification_count"] == 0
    assert not application.session_state["pending_context"]

    assert model.call_count == 2

    second_prompt = model.call_args_list[1].kwargs["prompt"]

    assert "How many customers are high risk?" in second_prompt
    assert "At least 70%." in second_prompt


def test_unsupported_request(app):
    application, model = app

    model.side_effect = None
    model.return_value = json.dumps(
        {
            "kind": "unsupported",
            "message": "Historical churn outcomes are not available.",
        }
    )

    submit_question(
        application,
        "How many customers actually churned last year?",
    )

    assert last_reply(application) == "Historical churn outcomes are not available."

    assert len(application.dataframe) == 0
    assert not application.session_state["pending_context"]


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
def test_displays_actionable_model_errors(app, error, expected):
    application, model = app

    model.side_effect = error

    submit_question(
        application,
        "How many customers are in the dataset?",
    )

    assert expected in last_reply(application)
    assert len(application.dataframe) == 0


def test_resets_conversation(app):
    application, model = app

    model.side_effect = None
    model.return_value = json.dumps(
        {
            "kind": "clarification",
            "question": "Which threshold should I use?",
        }
    )

    submit_question(application, "Show high-risk customers.")

    assert application.session_state["messages"]
    assert application.session_state["pending_context"]

    reset_button = next(
        button
        for button in application.sidebar.button
        if button.label == "New conversation"
    )

    reset_button.click().run()

    assert not application.exception
    assert not application.session_state["messages"]
    assert not application.session_state["pending_context"]
    assert application.session_state["clarification_count"] == 0

    assert model.call_count == 1
