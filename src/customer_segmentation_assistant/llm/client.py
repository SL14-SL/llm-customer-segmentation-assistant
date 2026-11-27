"""Shared client for structured Ollama model generation."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from customer_segmentation_assistant.config import (
    DEFAULT_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_CONTEXT_SIZE,
    OLLAMA_KEEP_ALIVE,
    OLLAMA_TEMPERATURE,
    OLLAMA_TIMEOUT_SECONDS,
)
from customer_segmentation_assistant.llm.exceptions import (
    OllamaConnectionError,
    OllamaHTTPError,
    OllamaResponseError,
    OllamaTimeoutError,
)


def generate_structured_response(
    *,
    system: str,
    prompt: str,
    schema: dict[str, object],
    model: str = DEFAULT_MODEL,
    num_predict: int = 512,
) -> str:
    """Generate a complete structured response without executing tools."""
    payload = {
        "model": model,
        "system": system,
        "prompt": prompt,
        "format": schema,
        "stream": False,
        "keep_alive": OLLAMA_KEEP_ALIVE,
        "options": {
            "temperature": OLLAMA_TEMPERATURE,
            "num_ctx": OLLAMA_CONTEXT_SIZE,
            "num_predict": num_predict,
        },
    }

    request = Request(
        f"{OLLAMA_BASE_URL}/api/generate",
        data=json.dumps(payload, allow_nan=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(
            request,
            timeout=OLLAMA_TIMEOUT_SECONDS,
        ) as response:
            generated = json.load(response)

    except HTTPError as error:
        raise OllamaHTTPError(error.code) from error

    except TimeoutError as error:
        raise OllamaTimeoutError(
            "Ollama did not respond within the configured "
            f"network timeout of {OLLAMA_TIMEOUT_SECONDS:g} seconds."
        ) from error

    except URLError as error:
        if isinstance(error.reason, TimeoutError):
            raise OllamaTimeoutError(
                "Ollama did not respond within the configured "
                f"network timeout of {OLLAMA_TIMEOUT_SECONDS:g} seconds."
            ) from error

        raise OllamaConnectionError(
            "Could not connect to the Ollama server."
        ) from error

    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise OllamaResponseError(
            "Ollama returned an invalid JSON response."
        ) from error

    except OSError as error:
        raise OllamaConnectionError(
            "Communication with the Ollama server failed."
        ) from error

    if not isinstance(generated, dict):
        raise OllamaResponseError("Ollama response must be a JSON object.")

    if generated.get("done") is not True or generated.get("done_reason") != "stop":
        raise OllamaResponseError("Ollama did not complete its response normally.")

    raw = generated.get("response")

    if not isinstance(raw, str) or not raw.strip():
        raise OllamaResponseError("Ollama returned an empty or invalid model response.")

    return raw
