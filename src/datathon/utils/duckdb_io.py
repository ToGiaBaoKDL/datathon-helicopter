from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import duckdb


@contextmanager
def connect(database_path: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    connection = duckdb.connect(str(database_path))
    try:
        yield connection
    finally:
        connection.close()
