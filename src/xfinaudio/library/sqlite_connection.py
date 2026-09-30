"""Operation-local SQLite transactions with deterministic resource ownership."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def database_connection(path: Path) -> Iterator[sqlite3.Connection]:
    """Commit or roll back the operation, then close even on setup failure."""
    connection = sqlite3.connect(path)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            yield connection
    finally:
        connection.close()
