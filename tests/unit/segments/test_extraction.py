"""Verify single-segment integration with the shared Ollama client."""

from unittest.mock import Mock

import pytest

from customer_segmentation_assistant.segments import extraction


def test_extracts_and_normalizes_segment_criteria(monkeypatch):
    generate = Mock(
        return_value=(
            '{"contract":"One year","minimum_churn_probability":0.7000000000000001}'
        )
    )

    monkeypatch.setattr(
        extraction,
        "generate_structured_response",
        generate,
    )

    question = "Annual contracts with churn probability at least 70%."

    criteria = extraction.extract_segment_criteria(
        question,
        model="test-model",
    )

    assert criteria == {
        "contract": "One year",
        "minimum_churn_probability": 0.7,
    }

    generate.assert_called_once_with(
        system=extraction.CRITERIA_SYSTEM_PROMPT,
        prompt=question,
        schema=extraction.CRITERIA_SCHEMA,
        model="test-model",
        num_predict=256,
    )


def test_rejects_invalid_extracted_criteria(monkeypatch):
    generate = Mock(
        return_value=('{"contract":"Invalid contract","minimum_churn_probability":0.7}')
    )

    monkeypatch.setattr(
        extraction,
        "generate_structured_response",
        generate,
    )

    with pytest.raises(ValueError, match="Unsupported contract type"):
        extraction.extract_segment_criteria("Test question")


def test_empty_question_does_not_call_model(monkeypatch):
    generate = Mock()

    monkeypatch.setattr(
        extraction,
        "generate_structured_response",
        generate,
    )

    with pytest.raises(ValueError, match="Question must not be empty"):
        extraction.extract_segment_criteria("   ")

    generate.assert_not_called()
