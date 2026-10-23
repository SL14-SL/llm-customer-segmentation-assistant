"""Verify CSV exports and protection against overwriting files."""

import pandas as pd
import pytest

from customer_segmentation_assistant.export import export_csv


def test_exports_query_result(tmp_path):
    result = pd.DataFrame({
        "customerID": ["customer-a", "customer-b"],
        "churn_probability": [0.8, 0.7],
    })
    destination = tmp_path / "exports" / "segment.csv"

    export_csv(result, destination)

    actual = pd.read_csv(destination)
    pd.testing.assert_frame_equal(actual, result)


def test_does_not_overwrite_existing_file(tmp_path):
    destination = tmp_path / "segment.csv"
    original_content = "existing export\n"
    destination.write_text(original_content, encoding="utf-8")

    result = pd.DataFrame({"customerID": ["customer-a"]})

    with pytest.raises(FileExistsError):
        export_csv(result, destination)

    assert destination.read_text(encoding="utf-8") == original_content