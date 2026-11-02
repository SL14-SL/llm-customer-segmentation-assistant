"""Verify summary requests and response handling without a running model."""

import json
from io import BytesIO

import pytest

from customer_segmentation_assistant import result_summary


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

    def fake_urlopen(request, timeout):
        captured.update(json.loads(request.data))
        assert timeout == 180
        return BytesIO(json.dumps({
            "done": True,
            "done_reason": "stop",
            "response": '{"answer":" One customer matches. "}',
        }).encode())

    monkeypatch.setattr(result_summary, "urlopen", fake_urlopen)

    result = example_result()
    result["customer_records"] = [{"customerID": "DO-NOT-SEND"}]

    answer = result_summary.explain_segment_result(result)

    assert answer == "One customer matches."
    assert json.loads(captured["prompt"]) == example_result()
    assert "DO-NOT-SEND" not in json.dumps(captured)


@pytest.mark.parametrize(
    "response",
    [
        {
            "done": True,
            "done_reason": "length",
            "response": '{"answer":"Incomplete"}',
        },
        {
            "done": True,
            "done_reason": "stop",
            "response": '{"answer":""}',
        },
        {
            "done": True,
            "done_reason": "stop",
            "response": '{"answer":"Text","extra":1}',
        },
        {
            "done": True,
            "done_reason": "stop",
            "response": "[]",
        },
    ],
)
def test_rejects_invalid_responses(monkeypatch, response):
    def fake_urlopen(request, timeout):
        return BytesIO(json.dumps(response).encode())

    monkeypatch.setattr(result_summary, "urlopen", fake_urlopen)

    with pytest.raises(ValueError):
        result_summary.explain_segment_result(example_result())