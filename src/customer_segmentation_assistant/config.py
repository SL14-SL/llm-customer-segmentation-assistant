"""Shared application and Ollama configuration."""

import math
import os

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:3b"
DEFAULT_OLLAMA_TIMEOUT = 180.0

OLLAMA_TEMPERATURE = 0
OLLAMA_CONTEXT_SIZE = 4096
OLLAMA_KEEP_ALIVE = "10m"


def parse_timeout(value: str) -> float:
    """Validate a positive and finite network timeout."""
    try:
        timeout = float(value)
    except ValueError as error:
        raise ValueError("OLLAMA_TIMEOUT_SECONDS must be a number.") from error

    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("OLLAMA_TIMEOUT_SECONDS must be positive and finite.")

    return timeout


OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    DEFAULT_OLLAMA_BASE_URL,
).rstrip("/")

DEFAULT_MODEL = os.getenv(
    "OLLAMA_MODEL",
    DEFAULT_OLLAMA_MODEL,
)

OLLAMA_TIMEOUT_SECONDS = parse_timeout(
    os.getenv(
        "OLLAMA_TIMEOUT_SECONDS",
        str(DEFAULT_OLLAMA_TIMEOUT),
    )
)
