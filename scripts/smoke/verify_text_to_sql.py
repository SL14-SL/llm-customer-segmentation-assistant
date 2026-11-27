"""Verify the synthetic Text-to-SQL database."""

from customer_segmentation_assistant.storage.database import query_dataframe


def main() -> None:
    """Check that the expected synthetic customer records are available."""
    result = query_dataframe("SELECT COUNT(*) AS customer_count FROM customers")

    count = int(result.iloc[0, 0])

    if count != 300:
        raise SystemExit(f"Expected 300 synthetic customers, received {count}.")

    print(f"Text-to-SQL demo verified: {count} customers.")


if __name__ == "__main__":
    main()
