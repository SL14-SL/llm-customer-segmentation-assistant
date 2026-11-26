"""Verify comparison extraction using the shared Ollama client."""

from unittest.mock import Mock

import pytest

from customer_segmentation_assistant.comparison import request


def test_extracts_and_normalizes_comparison_criteria(monkeypatch):
    generate = Mock(
        return_value=(
            '{"contracts":["Month-to-month","One year"],'
            '"minimum_probabilities":[0.7,0.7000000000000001],'
            '"unsupported_requirements":[]}'
        )
    )

    monkeypatch.setattr(
        request,
        "generate_structured_response",
        generate,
    )

    question = (
        "Compare monthly and annual contracts with churn probability at least 70%."
    )

    criteria = request.extract_comparison_criteria(
        question,
        model="test-model",
    )

    assert criteria == {
        "contracts": ["Month-to-month", "One year"],
        "minimum_churn_probability": 0.7,
    }

    generate.assert_called_once_with(
        system=request.EXTRACTION_PROMPT,
        prompt=question,
        schema=request.EXTRACTION_SCHEMA,
        model="test-model",
        num_predict=256,
    )


def test_preserves_model_detected_unsupported_requirements(monkeypatch):
    generate = Mock(
        return_value=(
            '{"contracts":["Month-to-month","One year"],'
            '"minimum_probabilities":[0.7],'
            '"unsupported_requirements":["Different thresholds"]}'
        )
    )

    monkeypatch.setattr(
        request,
        "generate_structured_response",
        generate,
    )

    decision = request.extract_comparison_criteria(
        "Compare monthly and annual contracts."
    )

    assert decision["kind"] == "unsupported"
    assert "Different thresholds" in decision["message"]


def test_empty_question_does_not_call_model(monkeypatch):
    generate = Mock()

    monkeypatch.setattr(
        request,
        "generate_structured_response",
        generate,
    )

    with pytest.raises(ValueError, match="Question must not be empty"):
        request.extract_comparison_criteria("   ")

    generate.assert_not_called()
