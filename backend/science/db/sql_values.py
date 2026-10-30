"""
Values and identifiers for SQL statements built by OutputSQL (sql.py).

Values are passed to the MySQL client as query parameters (cursor.execute(sql, params)), never pasted
into the statement text: a quote in a FITS header or a star name is then just data. Identifiers (schema,
table and column names) cannot be parameters, so they are validated and back-quoted instead.

No MySQL dependency, so tests/test_sql_values.py runs without a database.
"""
import math
import numbers
import re
from datetime import datetime, timezone

IDENTIFIER = re.compile(r'^[A-Za-z0-9_]+$')
# MySQL's limit for schema, table and column names
MAX_IDENTIFIER_LENGTH = 64


def quote_identifier(name: str) -> str:
    """A schema, table or column name, back-quoted; raises ValueError for anything but [A-Za-z0-9_]."""
    if not isinstance(name, str) or not IDENTIFIER.match(name) or len(name) > MAX_IDENTIFIER_LENGTH:
        raise ValueError(f"not a valid SQL identifier: {name!r}")
    return f"`{name}`"


def qualified_name(table_name: str, database: str) -> str:
    """`database`.`table_name`"""
    return f"{quote_identifier(database)}.{quote_identifier(table_name)}"


def placeholders(count: int) -> str:
    """(%s, %s, ...) for a row of `count` query parameters."""
    return "(" + ", ".join(["%s"] * count) + ")"


def sql_value(value):
    """
    A Python value as a query parameter for the MySQL client.

    bool -> 0/1, numpy numbers -> Python numbers, NaN and infinity -> NULL (MySQL has neither),
    time zone aware datetimes -> naive UTC (a DATETIME column has no time zone).
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real):
        value = float(value)
        return None if math.isnan(value) or math.isinf(value) else value
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value
    if isinstance(value, str):
        return value
    raise TypeError(f"no SQL conversion for {type(value).__name__}: {value!r}")
