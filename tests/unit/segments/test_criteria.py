"""Verify shared contract and probability validation."""

import pytest

from customer_segmentation_assistant.segments.criteria import (
    is_supported_contract,
    normalize_probability,
    validate_probability,
)


@pytest.mark.parametrize(
    "contract",
    [
        "Month-to-month",
        "One year",
        "Two year",
    ],
)
def test_accepts_supported_contract(contract):
    assert is_supported_contract(contract)


@pytest.mark.parametrize(
    "contract",
    [
        None,
        "",
        "Monthly",
        "Three year",
        123,
        True,
        [],
        {},
    ],
)
def test_rejects_unsupported_contract(contract):
    assert not is_supported_contract(contract)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, 0.0),
        (1, 1.0),
        (0.0, 0.0),
        (0.7, 0.7),
        (1.0, 1.0),
        (0.7000000000000001, 0.7000000000000001),
    ],
)
def test_validates_probability_without_rounding(value, expected):
    result = validate_probability(value)

    assert isinstance(result, float)
    assert result == expected


@pytest.mark.parametrize(
    "value",
    [
        None,
        True,
        False,
        "",
        "0.7",
        -0.1,
        1.1,
        float("nan"),
        float("inf"),
        float("-inf"),
        [],
        {},
        10**400,
    ],
)
def test_rejects_invalid_probability(value):
    with pytest.raises(
        ValueError,
        match="Minimum probability",
    ):
        validate_probability(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.7000000000000001, 0.7),
        (0.30000000000000004, 0.3),
        (0.9999999999999999, 1.0),
        (0.0, 0.0),
        (1.0, 1.0),
    ],
)
def test_normalizes_model_probability(value, expected):
    assert normalize_probability(value) == expected


def test_normalization_rejects_out_of_range_value():
    with pytest.raises(ValueError):
        normalize_probability(1.0000000000000002)


def test_supports_context_specific_error_message():
    with pytest.raises(
        ValueError,
        match="Custom validation error",
    ):
        validate_probability(
            -1,
            error_message="Custom validation error",
        )
