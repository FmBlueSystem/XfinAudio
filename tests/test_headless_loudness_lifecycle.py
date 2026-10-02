"""Deterministic cancellation, shutdown drainage, and stored scan identities."""

from __future__ import annotations

import io
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest

from tests.test_headless_protocol import messages, request
from xfinaudio.headless.cancellation import JobCancellationToken
from xfinaudio.headless.server import JsonlServer
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.track_repository import TrackRepository


def thread(function):
    result = threading.Thread(target=function, daemon=True)
    result.start()
    return result


def test_pre_cancelled_subscription_runs_once_even_after_repeated_cancel() -> None:
    token = JobCancellationToken()
    token.cancel()
    calls = []
    remove = token.subscribe(lambda: calls.append("drain"))
    assert calls == ["drain"]
    token.cancel()
    token.cancel()
    remove()
    remove()
    assert calls == ["drain"]


def test_retired_callback_is_not_called() -> None:
    token = JobCancellationToken()
    calls = []
    remove = token.subscribe(lambda: calls.append("unexpected"))
    remove()
    token.cancel()
    assert token.is_cancelled and calls == []


def test_retire_after_cancel_snapshot_prevents_late_callback() -> None:
    token = JobCancellationToken()
    entered, release = threading.Event(), threading.Event()
    calls = []

    def first():
        entered.set()
        assert release.wait(3)

    token.subscribe(first)
    remove = token.subscribe(lambda: calls.append("retired resource"))
    worker = thread(token.cancel)
    try:
        assert entered.wait(3)
        remove()
    finally:
        release.set()
        worker.join(3)
    assert not worker.is_alive() and calls == []


def test_callback_retirement_drains_already_started_callback() -> None:
    token = JobCancellationToken()
    entered, release, retired = threading.Event(), threading.Event(), threading.Event()

    def drain():
        entered.set()
        assert release.wait(3)

    remove = token.subscribe(drain)
    cancelling = thread(token.cancel)
    assert entered.wait(3)
    retiring = thread(lambda: (remove(), retired.set()))
    try:
        assert not retired.wait(0.05)
    finally:
        release.set()
        cancelling.join(3)
        retiring.join(3)
    assert retired.is_set() and not cancelling.is_alive() and not retiring.is_alive()


def test_concurrent_subscribe_and_cancel_are_exactly_once() -> None:
    def once():
        token = JobCancellationToken()
        barrier = threading.Barrier(3)
        calls = []
        removers = []
        subscribing = thread(lambda: (barrier.wait(3), removers.append(token.subscribe(lambda: calls.append(1)))))
        cancelling = thread(lambda: (barrier.wait(3), token.cancel()))
        barrier.wait(3)
        subscribing.join(3)
        cancelling.join(3)
        token.cancel()
        assert calls == [1]
        removers[0]()

    for _ in range(30):
        once()


def test_callbacks_can_remove_and_subscribe_without_holding_token_lock() -> None:
    token = JobCancellationToken()
    calls = []

    def callback():
        remove()
        token.subscribe(lambda: calls.append("nested"))()
        calls.append("outer")

    remove = token.subscribe(callback)
    worker = thread(token.cancel)
    worker.join(3)
    assert not worker.is_alive() and calls == ["nested", "outer"]


class DrainingBackend:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.cancel_started = threading.Event()
        self.release_commit = threading.Event()
        self.commit_finished = threading.Event()
        self.children_finished = threading.Event()
        self.shutdown_started = threading.Event()
        self.shutdown_release = threading.Event()
        self.cancel_calls = 0
        self.shutdown_calls = 0
        self.saw_cancelled = False

    def execute(self, method, params, *, cancellation_token, progress):
        assert method == "loudness.run"

        def drain():
            self.cancel_calls += 1
            self.cancel_started.set()
            assert self.commit_finished.wait(3)
            self.children_finished.set()

        remove = cancellation_token.subscribe(drain)
        self.started.set()
        try:
            assert self.release_commit.wait(3)
            # Real tag completion can emit owned-write progress while cancelling.
            progress({"phase": "loudness_write", "trackIds": []})
            self.commit_finished.set()
            self.saw_cancelled = cancellation_token.is_cancelled
            return {"cancelled": self.saw_cancelled, "changedCount": 1}
        finally:
            remove()

    def shutdown(self):
        self.shutdown_calls += 1
        assert self.commit_finished.is_set() and self.children_finished.is_set()
        self.shutdown_started.set()
        assert self.shutdown_release.wait(3)


@pytest.mark.parametrize("via_request", [False, True])
def test_close_or_cancel_drains_active_commit_outside_server_lock(via_request: bool) -> None:
    backend = DrainingBackend()
    output = io.StringIO()
    server = JsonlServer(cast(Any, backend), output)
    job_id = str(uuid4())
    server.process_line(request("loudness.run", {"previewId": str(uuid4()), "confirmed": True}, job_id))
    assert backend.started.wait(3)
    finished = threading.Event()
    action = (lambda: server.process_line(request("cancel", {"jobId": job_id}))) if via_request else server.close
    stopping = thread(lambda: (action(), finished.set()))
    try:
        assert backend.cancel_started.wait(3)
        assert not finished.wait(0.05)
        backend.release_commit.set()
        assert backend.commit_finished.wait(1), "server lock blocked the commit's final progress"
        assert backend.children_finished.wait(1)
        if via_request:
            stopping.join(3)
            assert finished.is_set()
            stopping = thread(lambda: (server.close(), finished.set()))
        assert backend.shutdown_started.wait(1)
        assert stopping.is_alive(), "close returned before backend child drainage"
    finally:
        backend.release_commit.set()
        backend.shutdown_release.set()
        stopping.join(4)
    assert not stopping.is_alive() and backend.saw_cancelled
    assert backend.cancel_calls == backend.shutdown_calls == 1
    assert any(item.get("result", {}).get("changedCount") == 1 for item in messages(output))
    assert not any(item.get("event") == "progress" for item in messages(output))
    server.close()
    assert backend.shutdown_calls == 1


def test_shutdown_request_and_run_finally_call_backend_shutdown_once() -> None:
    calls = []
    backend = cast(Any, type("Backend", (), {"shutdown": lambda self: calls.append("shutdown")})())
    output = io.StringIO()
    server = JsonlServer(backend, output)
    server.run(io.BytesIO(request("shutdown")))
    server.close()
    assert calls == ["shutdown"]
    assert messages(output)[-1]["result"] == {"shutdown": True}


def test_fake_backend_without_shutdown_remains_compatible() -> None:
    server = JsonlServer(cast(Any, object()), io.StringIO())
    server.close()
    server.close()


def test_stored_scan_identities_handle_empty_unknown_and_missing_files(tmp_path: Path) -> None:
    repository = TrackRepository(tmp_path / "tracks.db")
    path = tmp_path / "fixture.flac"
    path.write_bytes(b"owned metadata fixture")
    before = path.stat()
    missing = str(tmp_path / "not-on-disk.flac")
    repository.save_scan_results([TrackRecord(path=str(path)), TrackRecord(path=missing)])
    path.write_bytes(b"changed after scan")
    assert repository.load_scan_file_identities([]) == {}
    assert repository.load_scan_file_identities(["unknown"]) == {}
    assert repository.load_scan_file_identities(iter([str(path), missing, "unknown", str(path)])) == {
        str(path): (before.st_mtime_ns, before.st_size),
        missing: (None, None),
    }


def test_stored_scan_identities_chunk_queries_beyond_sqlite_limit(tmp_path: Path, monkeypatch) -> None:
    repository = TrackRepository(tmp_path / "tracks.db")
    paths = [str(tmp_path / f"unavailable-{index}.flac") for index in range(1803)]
    repository.save_scan_results(TrackRecord(path=path) for path in paths)
    connect = repository._connect
    queries = []

    @contextmanager
    def bounded_connection():
        with connect() as connection:
            connection.setlimit(sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER, 900)
            connection.set_trace_callback(lambda sql: queries.append(sql) if sql.startswith("SELECT path,") else None)
            yield connection

    monkeypatch.setattr(repository, "_connect", bounded_connection)
    assert repository.load_scan_file_identities(paths) == dict.fromkeys(paths, (None, None))
    assert len(queries) == 3


def test_failed_hook_does_not_skip_remaining_drains_or_reinvoke(caplog) -> None:
    token = JobCancellationToken()
    calls = []

    def failing():
        calls.append("failed")
        raise OSError("synthetic cancellation failure")

    token.subscribe(failing)
    token.subscribe(lambda: calls.append("drained"))
    token.cancel()
    token.cancel()
    assert calls == ["failed", "drained"]
    assert "Cancellation resource hook failed" in caplog.text
