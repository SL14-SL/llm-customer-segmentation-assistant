"""Verify capability rules independently of requirement extraction quality."""

import json

import pytest

from customer_segmentation_assistant.comparison_scope import (
    parse_scope_requirements,
    unsupported_requirements,
)


def requirements(*, conditions=None, extras=None, outputs=None):
    return {
        "probability_conditions": conditions if conditions is not None else [],
        "additional_requirements": extras if extras is not None else [],
        "requested_outputs": outputs if outputs is not None else [],
    }


def test_same_threshold_for_multiple_groups_is_supported():
    result = unsupported_requirements(requirements(
        conditions=[
            {"operator": "gte", "value": 0.6},
            {"operator": "gte", "value": 0.6},
        ],
        outputs=["customer_count"],
    ))

    assert result == []


def test_different_thresholds_are_rejected():
    result = unsupported_requirements(requirements(
        conditions=[
            {"operator": "gte", "value": 0.4},
            {"operator": "gte", "value": 0.75},
        ],
    ))

    assert any("Different probability thresholds" in item for item in result)


def test_missing_threshold_is_not_unsupported():
    assert unsupported_requirements(requirements()) == []


def test_zero_minimum_is_supported():
    assert unsupported_requirements(requirements(
        conditions=[{"operator": "gte", "value": 0.0}],
    )) == []


@pytest.mark.parametrize("operator", ["gt", "lte", "lt", "eq"])
def test_unsupported_probability_operators(operator):
    assert unsupported_requirements(requirements(
        conditions=[{"operator": operator, "value": 0.5}],
    ))


@pytest.mark.parametrize(
    "output",
    ["observed_churn_count", "customer_list", "historical_analysis", "other"],
)
def test_unavailable_outputs_are_rejected(output):
    assert unsupported_requirements(requirements(outputs=[output]))


def test_additional_filter_is_rejected():
    assert unsupported_requirements(requirements(
        extras=["tenure of at least 24 months"],
    )) == ["tenure of at least 24 months"]


@pytest.mark.parametrize(
    "value",
    [True, "0.5", -0.1, 1.1, float("nan"), float("inf")],
)
def test_invalid_probability_values_are_rejected(value):
    raw = json.dumps(requirements(
        conditions=[{"operator": "gte", "value": value}],
    ))

    with pytest.raises(ValueError):
        parse_scope_requirements(raw)