"""Operation-local SQLite transactions with deterministic resource ownership."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

# A lock wait must be a documented, tested contract instead of an implicit
# driver default. 5000 ms is long enough for a concurrent scan to commit one
# transaction and short enough that a hung writer surfaces as an error.
BUSY_TIMEOUT_MS = 5000


@contextmanager
def database_connection(path: Path) -> Iterator[sqlite3.Connection]:
    """Commit or roll back the operation, then close even on setup failure.

    The journal mode stays SQLite's rollback default on purpose: WAL creates
    ``-wal``/``-shm`` sidecars, and ``headless/legacy_source.py`` refuses a data
    directory that carries them and compares the two databases byte by byte.
    """
    connection = sqlite3.connect(path, timeout=BUSY_TIMEOUT_MS / 1000)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
        with connection:
            yield connection
    finally:
        connection.close()
