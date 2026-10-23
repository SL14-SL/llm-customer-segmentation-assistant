"""Export query results without overwriting existing files."""

from pathlib import Path

import pandas as pd


def export_csv(result: pd.DataFrame, destination: Path) -> None:
    """Write a CSV file, failing if the destination already exists."""
    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open(
        mode="x",
        encoding="utf-8",
        newline="",
    ) as handle:
        result.to_csv(handle, index=False)