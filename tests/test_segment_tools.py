"""Verify segment summaries using independent synthetic expectations."""

import pytest

from customer_segmentation_assistant.demo_data import create_demo_database
from customer_segmentation_assistant.tools import summarize_segment


@pytest.fixture
def demo_database(tmp_path):
    path = tmp_path / "demo.duckdb"
    create_demo_database(path)
    return path


@pytest.mark.parametrize(
    ("contract", "expected_charge", "expected_probability"),
    [
        ("Month-to-month", 75.0, 0.75),
        ("One year", 60.0, 0.75),
    ],
)
def test_segment_summary(
    demo_database,
    contract,
    expected_charge,
    expected_probability,
):
    result = summarize_segment(
        contract=contract,
        minimum_churn_probability=0.65,
        database=demo_database,
    )

    assert result["customer_count"] == 2
    assert result["average_monthly_charges"] == pytest.approx(expected_charge)
    assert result["average_churn_probability"] == pytest.approx(
        expected_probability
    )
    assert result["contract"] == contract
    assert result["minimum_churn_probability"] == 0.65
    assert "customerID" not in result


def test_empty_segment_has_no_averages(demo_database):
    result = summarize_segment(
        contract="Two year",
        minimum_churn_probability=0.65,
        database=demo_database,
    )

    assert result["customer_count"] == 0
    assert result["average_monthly_charges"] is None
    assert result["average_churn_probability"] is None


@pytest.mark.parametrize(
    "threshold",
    [-0.1, 1.1, float("nan"), float("inf"), True, "0.65", None],
)
def test_rejects_invalid_threshold(demo_database, threshold):
    with pytest.raises(ValueError, match="finite number"):
        summarize_segment(
            contract="One year",
            minimum_churn_probability=threshold,
            database=demo_database,
        )


def test_rejects_unapproved_contract(demo_database):
    with pytest.raises(ValueError, match="Unsupported contract"):
        summarize_segment(
            contract="One year' OR 1=1 --",
            minimum_churn_probability=0.65,
            database=demo_database,
        )


def test_demo_creation_preserves_existing_database(demo_database):
    with pytest.raises(FileExistsError):
        create_demo_database(demo_database)

    result = summarize_segment(
        contract="Month-to-month",
        minimum_churn_probability=0,
        database=demo_database,
    )
    assert result["customer_count"] == 3