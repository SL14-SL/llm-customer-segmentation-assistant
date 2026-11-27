"""Provide user-friendly messages for Ollama communication errors."""

from customer_segmentation_assistant.llm.exceptions import (
    OllamaConnectionError,
    OllamaError,
    OllamaHTTPError,
    OllamaResponseError,
    OllamaTimeoutError,
)


def format_ollama_error(error: OllamaError) -> str:
    """Convert a technical Ollama error into an actionable message."""
    if isinstance(error, OllamaTimeoutError):
        return (
            "The model request timed out. "
            "Try again or increase OLLAMA_TIMEOUT_SECONDS. "
            "Avoid concurrent model requests on slower hardware."
        )

    if isinstance(error, OllamaConnectionError):
        return (
            "Could not connect to Ollama. "
            "Check whether the Ollama server is running and reachable."
        )

    if isinstance(error, OllamaHTTPError):
        if error.status_code == 404:
            return (
                "Ollama returned HTTP 404. "
                "Check whether the configured model is available "
                "and the Ollama endpoint is correct."
            )

        if error.status_code >= 500:
            return (
                f"Ollama returned a server error ({error.status_code}). "
                "Check the server logs and available system resources."
            )

        return (
            f"Ollama rejected the request (HTTP {error.status_code}). "
            "Check the model and server configuration."
        )

    if isinstance(error, OllamaResponseError):
        return (
            "The model returned an incomplete or invalid response. "
            "Please try again or rephrase your request."
        )

    return (
        "An error occurred while communicating with Ollama. "
        "Please try again or check the server configuration."
    )
