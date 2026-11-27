"""Verify summary requests and response handling without a running model."""

import json

import pytest

from customer_segmentation_assistant.experiments import result_summary
from customer_segmentation_assistant.llm.exceptions import OllamaResponseError


def example_result():
    return {
        "contract": "One year",
        "minimum_churn_probability": 0.7,
        "customer_count": 1,
        "average_monthly_charges": 70.0,
        "average_churn_probability": 0.85,
    }


def test_sends_only_aggregate_fields(monkeypatch):
    captured = {}

    def fake_generate(**kwargs):
        captured.update(kwargs)
        return '{"answer":" One customer matches. "}'

    monkeypatch.setattr(
        result_summary,
        "generate_structured_response",
        fake_generate,
    )

    result = example_result()
    result["customer_records"] = [{"customerID": "DO-NOT-SEND"}]

    answer = result_summary.explain_segment_result(result)

    assert answer == "One customer matches."
    assert json.loads(captured["prompt"]) == example_result()
    assert "DO-NOT-SEND" not in json.dumps(captured)

    assert captured["system"] == result_summary.SUMMARY_SYSTEM_PROMPT
    assert captured["schema"] == result_summary.SUMMARY_SCHEMA
    assert captured["model"] == result_summary.DEFAULT_MODEL
    assert captured["num_predict"] == 256


@pytest.mark.parametrize(
    "response",
    [
        '{"answer":""}',
        '{"answer":"   "}',
        '{"answer":"Text","extra":1}',
        "[]",
        "{}",
        '{"answer":123}',
        "invalid json",
    ],
)
def test_rejects_invalid_responses(monkeypatch, response):
    def fake_generate(**kwargs):
        return response

    monkeypatch.setattr(
        result_summary,
        "generate_structured_response",
        fake_generate,
    )

    with pytest.raises(ValueError):
        result_summary.explain_segment_result(example_result())


def test_propagates_incomplete_model_response(monkeypatch):
    def fake_generate(**kwargs):
        raise OllamaResponseError("Ollama did not complete its response normally.")

    monkeypatch.setattr(
        result_summary,
        "generate_structured_response",
        fake_generate,
    )

    with pytest.raises(OllamaResponseError):
        result_summary.explain_segment_result(example_result())


def test_missing_fields_do_not_trigger_model_call(monkeypatch):
    def unexpected_model_call(**kwargs):
        pytest.fail("Ollama must not be called for incomplete results.")

    monkeypatch.setattr(
        result_summary,
        "generate_structured_response",
        unexpected_model_call,
    )

    result = example_result()
    del result["customer_count"]

    with pytest.raises(ValueError, match="Missing result fields"):
        result_summary.explain_segment_result(result)
