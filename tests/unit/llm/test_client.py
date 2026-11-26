"""Verify shared Ollama communication without live inference."""

import io
import json
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

import pytest

from customer_segmentation_assistant.llm import client
from customer_segmentation_assistant.llm.exceptions import (
    OllamaConnectionError,
    OllamaHTTPError,
    OllamaResponseError,
    OllamaTimeoutError,
)

TEST_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
    },
    "required": ["answer"],
}


def generate():
    """Execute a representative structured model request."""
    return client.generate_structured_response(
        system="Return JSON.",
        prompt="Test question",
        schema=TEST_SCHEMA,
        model="test-model",
        num_predict=256,
    )


def mock_response(monkeypatch, payload):
    """Provide an in-memory HTTP response."""
    response = io.BytesIO(json.dumps(payload).encode("utf-8"))
    mocked = Mock(return_value=response)

    monkeypatch.setattr(client, "urlopen", mocked)

    return mocked


def test_successful_generation(monkeypatch):
    raw = '{"answer": "Test answer"}'

    mock_response(
        monkeypatch,
        {
            "done": True,
            "done_reason": "stop",
            "response": raw,
        },
    )

    assert generate() == raw


def test_request_payload(monkeypatch):
    mocked = mock_response(
        monkeypatch,
        {
            "done": True,
            "done_reason": "stop",
            "response": '{"answer": "ok"}',
        },
    )

    monkeypatch.setattr(
        client,
        "OLLAMA_BASE_URL",
        "http://test-ollama:11434",
    )
    monkeypatch.setattr(
        client,
        "OLLAMA_TIMEOUT_SECONDS",
        300.0,
    )

    generate()

    request = mocked.call_args.args[0]
    kwargs = mocked.call_args.kwargs
    payload = json.loads(request.data.decode("utf-8"))

    assert request.full_url == "http://test-ollama:11434/api/generate"
    assert request.get_method() == "POST"
    assert request.get_header("Content-type") == "application/json"

    assert kwargs["timeout"] == 300.0

    assert payload == {
        "model": "test-model",
        "system": "Return JSON.",
        "prompt": "Test question",
        "format": TEST_SCHEMA,
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "temperature": 0,
            "num_ctx": 4096,
            "num_predict": 256,
        },
    }


@pytest.mark.parametrize(
    "payload",
    [
        [],
        None,
        {},
        {
            "done": False,
            "done_reason": "stop",
            "response": "{}",
        },
        {
            "done": True,
            "done_reason": "length",
            "response": "{}",
        },
        {
            "done": True,
            "response": "{}",
        },
        {
            "done": True,
            "done_reason": "stop",
        },
        {
            "done": True,
            "done_reason": "stop",
            "response": "",
        },
        {
            "done": True,
            "done_reason": "stop",
            "response": "   ",
        },
        {
            "done": True,
            "done_reason": "stop",
            "response": 123,
        },
    ],
)
def test_rejects_invalid_response(monkeypatch, payload):
    mock_response(monkeypatch, payload)

    with pytest.raises(OllamaResponseError):
        generate()


def test_rejects_invalid_json(monkeypatch):
    monkeypatch.setattr(
        client,
        "urlopen",
        Mock(return_value=io.BytesIO(b"invalid json")),
    )

    with pytest.raises(
        OllamaResponseError,
        match="invalid JSON",
    ):
        generate()


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError("timed out"),
        URLError(TimeoutError("timed out")),
    ],
)
def test_timeout(monkeypatch, error):
    mocked = Mock(side_effect=error)
    monkeypatch.setattr(client, "urlopen", mocked)

    with pytest.raises(OllamaTimeoutError):
        generate()

    assert mocked.call_count == 1


@pytest.mark.parametrize(
    "error",
    [
        URLError("connection refused"),
        ConnectionRefusedError("connection refused"),
        ConnectionResetError("connection reset"),
    ],
)
def test_connection_error(monkeypatch, error):
    monkeypatch.setattr(
        client,
        "urlopen",
        Mock(side_effect=error),
    )

    with pytest.raises(OllamaConnectionError):
        generate()


@pytest.mark.parametrize("status_code", [400, 404, 500, 503])
def test_http_error(monkeypatch, status_code):
    error = HTTPError(
        url="http://localhost:11434/api/generate",
        code=status_code,
        msg="API error",
        hdrs=None,
        fp=None,
    )

    monkeypatch.setattr(
        client,
        "urlopen",
        Mock(side_effect=error),
    )

    with pytest.raises(OllamaHTTPError) as captured:
        generate()

    assert captured.value.status_code == status_code
