"""Exceptions raised by the shared Ollama client."""


class OllamaError(RuntimeError):
    """Base exception for Ollama communication failures."""


class OllamaConnectionError(OllamaError):
    """Raised when the Ollama server cannot be reached."""


class OllamaTimeoutError(OllamaError):
    """Raised when an Ollama request exceeds its network timeout."""


class OllamaHTTPError(OllamaError):
    """Raised when the Ollama API returns an HTTP error."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"Ollama returned HTTP status {status_code}.")


class OllamaResponseError(OllamaError):
    """Raised when Ollama returns an invalid or incomplete response."""
