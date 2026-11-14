"""Pin the SQLite connection contract every repository inherits (spec S9).

The audit asked for ``journal_mode=WAL`` plus ``busy_timeout=5000``. Revised by
log entry L6, this batch only makes the 5000 ms busy timeout explicit: WAL
sidecar files (``-wal``, ``-shm``) would invalidate the byte-level snapshots the
legacy importer compares (see ``xfinaudio/headless/legacy_source.py``), so the
journal mode must stay SQLite's rollback default.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from xfinaudio.library.sqlite_connection import database_connection

EXPECTED_BUSY_TIMEOUT_MS = 5000


def test_database_connection_pins_the_5000_ms_busy_timeout(tmp_path: Path) -> None:
    with database_connection(tmp_path / "library.db") as connection:
        assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == EXPECTED_BUSY_TIMEOUT_MS


def test_database_connection_keeps_foreign_keys_enforced(tmp_path: Path) -> None:
    with database_connection(tmp_path / "library.db") as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_database_connection_keeps_the_rollback_journal_mode(tmp_path: Path) -> None:
    with database_connection(tmp_path / "library.db") as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
        connection.execute("CREATE TABLE probe (value TEXT)")

    # No -wal/-shm sidecars: the legacy importer refuses a data directory that
    # carries them, so opening the database must not create any.
    assert sorted(path.name for path in tmp_path.iterdir()) == ["library.db"]


def test_database_connection_waits_for_a_concurrent_write_instead_of_failing(tmp_path: Path) -> None:
    db_path = tmp_path / "library.db"
    with database_connection(db_path) as setup:
        setup.execute("CREATE TABLE probe (value TEXT)")

    holder = sqlite3.connect(db_path, isolation_level=None, check_same_thread=False)
    holder.execute("BEGIN IMMEDIATE")
    attempted = threading.Event()

    def release() -> None:
        attempted.wait(timeout=10)
        time.sleep(0.25)
        holder.execute("COMMIT")

    thread = threading.Thread(target=release)
    thread.start()
    try:
        with database_connection(db_path) as connection:
            attempted.set()
            started = time.monotonic()
            connection.execute("INSERT INTO probe (value) VALUES ('waited')")
            waited = time.monotonic() - started
    finally:
        attempted.set()
        thread.join(timeout=10)
        holder.close()

    assert not thread.is_alive()
    assert waited >= 0.05
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT count(*) FROM probe").fetchone()[0] == 1
