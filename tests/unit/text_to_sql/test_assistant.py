"""Verify Text-to-SQL integration with the shared Ollama client."""

from unittest.mock import Mock

import pytest

from customer_segmentation_assistant.text_to_sql import assistant
from customer_segmentation_assistant.text_to_sql.decisions import (
    ClarificationDecision,
    QueryDecision,
    UnsupportedDecision,
)


@pytest.mark.parametrize(
    ("response", "expected_type"),
    [
        (
            '{"kind":"query","sql":"SELECT COUNT(*) FROM customers"}',
            QueryDecision,
        ),
        (
            '{"kind":"clarification","question":"Which threshold?"}',
            ClarificationDecision,
        ),
        (
            '{"kind":"unsupported","message":"Historical data unavailable."}',
            UnsupportedDecision,
        ),
    ],
)
def test_generates_validated_decision(
    monkeypatch,
    response,
    expected_type,
):
    generate = Mock(return_value=response)

    monkeypatch.setattr(
        assistant,
        "generate_structured_response",
        generate,
    )

    decision = assistant.generate_decision(
        "Test customer question",
        model="test-model",
    )

    assert isinstance(decision, expected_type)

    generate.assert_called_once_with(
        system=assistant.SYSTEM_PROMPT,
        prompt="Test customer question",
        schema=assistant.DECISION_SCHEMA,
        model="test-model",
        num_predict=512,
    )


def test_empty_question_does_not_call_model(monkeypatch):
    generate = Mock()

    monkeypatch.setattr(
        assistant,
        "generate_structured_response",
        generate,
    )

    with pytest.raises(ValueError, match="Question must not be empty"):
        assistant.generate_decision("   ")

    generate.assert_not_called()
