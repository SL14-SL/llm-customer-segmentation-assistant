"""Restrict queries to a small supported SQL subset."""

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

ALLOWED_NODES = frozenset({
    "Select", "From", "Table", "TableAlias",
    "Column", "Identifier", "Star", "Alias",
    "Literal", "Null", "Boolean", "Placeholder",
    "Where", "And", "Or", "Not", "Paren",
    "EQ", "NEQ", "GT", "GTE", "LT", "LTE",
    "Is", "In", "Between", "Like",
    "Order", "Ordered", "Limit", "Group",
    "Count", "Avg", "Sum", "Min", "Max",
    "Distinct", "Neg",
})


def validate_sql(sql: str) -> None:
    """Reject unsupported statements, sources and expressions."""
    try:
        statements = sqlglot.parse(sql, read="duckdb")
    except SqlglotError as error:
        raise ValueError("Invalid SQL.") from error

    if len(statements) != 1 or statements[0] is None:
        raise ValueError("Exactly one SQL statement is required.")

    statement = statements[0]

    if not isinstance(statement, exp.Select):
        raise ValueError("Only SELECT statements are allowed.")  # noqa: TRY004 - SQL policy violation

    for node in statement.walk():
        if type(node).__name__ not in ALLOWED_NODES:
            raise ValueError(
                f"Unsupported SQL expression: {type(node).__name__}"
            )

    tables = list(statement.find_all(exp.Table))

    if len(tables) != 1:
        raise ValueError("Query exactly one customers table.")

    table = tables[0]

    if (
        not isinstance(table.this, exp.Identifier)
        or table.name.lower() != "customers"
        or table.db
        or table.catalog
    ):
        raise ValueError("Only the unqualified customers table is allowed.")
