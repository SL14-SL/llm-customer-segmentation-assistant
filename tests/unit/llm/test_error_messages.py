"""Verify actionable messages for Ollama communication errors."""

import pytest

from customer_segmentation_assistant.llm.error_messages import (
    format_ollama_error,
)
from customer_segmentation_assistant.llm.exceptions import (
    OllamaConnectionError,
    OllamaError,
    OllamaHTTPError,
    OllamaResponseError,
    OllamaTimeoutError,
)


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            OllamaTimeoutError("Technical timeout"),
            "OLLAMA_TIMEOUT_SECONDS",
        ),
        (
            OllamaConnectionError("Connection refused"),
            "Check whether the Ollama server is running",
        ),
        (
            OllamaHTTPError(404),
            "configured model is available",
        ),
        (
            OllamaHTTPError(400),
            "HTTP 400",
        ),
        (
            OllamaHTTPError(500),
            "server error (500)",
        ),
        (
            OllamaHTTPError(503),
            "server error (503)",
        ),
        (
            OllamaResponseError("Invalid response"),
            "incomplete or invalid response",
        ),
        (
            OllamaError("Unknown error"),
            "An error occurred while communicating with Ollama",
        ),
    ],
)
def test_formats_actionable_error_message(error, expected):
    assert expected in format_ollama_error(error)


def test_does_not_expose_internal_exception_details():
    error = OllamaConnectionError("Internal technical details: DO-NOT-DISPLAY")

    message = format_ollama_error(error)

    assert "DO-NOT-DISPLAY" not in message
