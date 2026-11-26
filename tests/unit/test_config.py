"""Verify shared Ollama configuration."""

import pytest

from customer_segmentation_assistant.config import parse_timeout


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("180", 180.0),
        ("300", 300.0),
        ("600", 600.0),
        ("0.5", 0.5),
        ("120.5", 120.5),
        (" 180 ", 180.0),
    ],
)
def test_accepts_valid_timeout(value, expected):
    assert parse_timeout(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "invalid",
        "0",
        "-1",
        "nan",
        "inf",
        "-inf",
    ],
)
def test_rejects_invalid_timeout(value):
    with pytest.raises(ValueError, match="OLLAMA_TIMEOUT_SECONDS"):
        parse_timeout(value)
