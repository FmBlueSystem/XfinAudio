"""JSONL transport validation, cancellation, and shutdown ownership."""

from __future__ import annotations

import io
import json
import threading
from pathlib import Path
from uuid import uuid4

from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.server import INLINE_METHODS, MAX_LINE_BYTES, JsonlServer

# The reviewed contract: every query a read-only screen may need while the single job
# worker is occupied. Each one is answerable from an owned connection or in-memory
# snapshot, so none of them can mutate state or interfere with the running job.
EXPECTED_INLINE_METHODS = frozenset(
    {
        "ai.status",
        "library.list",
        "library.query",
        "live.status",
        "loudness.status",
        "metadata.report",
        "playlist.compare",
        "playlist.deleted.list",
        "playlist.list",
        "playlist.open",
        "playlist.search",
        "prep.catalog",
        "prep.settings.get",
        "profiles.settings.get",
        "profiles.status",
        "settings.get",
        "track.resolve",
    }
)
# Mutating or job-controlling commands that keep the exact busy refusal during a job.
EXPECTED_REFUSED_METHODS = (
    "ai.apply",
    "ai.credential.set",
    "ai.prepare",
    "ai.run",
    "library.rescan",
    "library.scan",
    "legacy.preview",
    "loudness.run",
    "playlist.delete.commit",
    "playlist.delete.preview",
    "playlist.edit.save",
    "playlist.rename",
    "playlist.restore",
    "playlist.save",
    "prep.generate",
    "prep.select",
    "profiles.complete",
    "review.remove",
    "serato.commit",
    "settings.update",
)


def request(method: str, params: dict | None = None, request_id: str | None = None) -> bytes:
    return (json.dumps({"id": request_id or str(uuid4()), "method": method, "params": params or {}}) + "\n").encode()


def messages(output: io.StringIO) -> list[dict]:
    return [json.loads(line) for line in output.getvalue().splitlines()]


def test_protocol_recovers_from_invalid_json_shape_and_oversize(tmp_path: Path) -> None:
    output = io.StringIO()
    source = io.BytesIO(b"{bad}\n[]\n" + b"x" * (MAX_LINE_BYTES + 1) + b"\n" + request("shutdown"))
    JsonlServer(HeadlessBackend(tmp_path), output).run(source)
    result = messages(output)
    assert len(result) == 4
    assert [item["error"]["code"] for item in result[:-1]] == ["invalid_request"] * 3
    assert result[-1]["result"] == {"shutdown": True}


def test_worker_serialization_cancellation_and_shutdown(tmp_path: Path) -> None:
    started = threading.Event()
    released = threading.Event()

    class SlowBackend(HeadlessBackend):
        def execute(self, method, params, *, cancellation_token=None, progress=None):
            started.set()
            assert released.wait(5)
            assert cancellation_token is not None and cancellation_token.is_cancelled
            if progress:
                progress({"phase": "scan", "processedCount": 1, "totalCount": 1})
            return {"cancelled": True}

    output = io.StringIO()
    server = JsonlServer(SlowBackend(tmp_path), output)
    job_id = str(uuid4())
    server.process_line(request("library.scan", {"root": "/somewhere"}, job_id))
    assert started.wait(5)
    # A write command stays refused; only the reviewed read-only queries answer inline.
    server.process_line(request("playlist.rename", {"playlistId": 1, "name": "Set"}))
    server.process_line(request("cancel", {"jobId": str(uuid4())}))
    server.process_line(request("cancel", {"jobId": job_id}))
    released.set()
    server.close()
    result = messages(output)
    assert result[0]["error"]["code"] == "busy"
    assert result[1]["result"] == {"cancelled": False}
    assert result[2]["result"] == {"cancelled": True}
    assert result[3]["id"] == job_id
    assert result[3]["result"]["cancelled"] is True
    assert not any("event" in item for item in result)


def test_unknown_method_is_safe_and_preserves_request_id(tmp_path: Path) -> None:
    output = io.StringIO()
    server = JsonlServer(HeadlessBackend(tmp_path), output)
    request_id = str(uuid4())
    server.process_line(request("anything", request_id=request_id))
    server.close()
    result = messages(output)[0]
    assert result == {"id": request_id, "ok": False, "error": {"code": "unknown_method", "message": "Unknown command"}}


def test_deeply_nested_json_is_rejected_without_crashing(tmp_path: Path) -> None:
    output = io.StringIO()
    server = JsonlServer(HeadlessBackend(tmp_path), output)
    server.process_line(b"[" * 10000 + b"0" + b"]" * 10000 + b"\n")
    assert messages(output)[0]["error"]["code"] == "invalid_request"


def test_track_resolution_remains_available_during_active_job(tmp_path: Path) -> None:
    started = threading.Event()
    release = threading.Event()

    class Backend(HeadlessBackend):
        def execute(self, method, params, *, cancellation_token=None, progress=None):
            if method == "track.resolve":
                return {"path": "/authorized/track.flac", "mime": "audio/flac"}
            started.set()
            assert release.wait(5)
            return {}

    output = io.StringIO()
    server = JsonlServer(Backend(tmp_path), output)
    server.process_line(request("prep.generate", {"targetTrackCount": 2}))
    assert started.wait(5)
    try:
        server.process_line(request("track.resolve", {"trackId": "opaque"}))
        assert messages(output)[0]["ok"] is True
        assert messages(output)[0]["result"]["mime"] == "audio/flac"
    finally:
        release.set()
        server.close()


def test_inline_methods_are_exactly_the_reviewed_read_only_queries() -> None:
    assert INLINE_METHODS == EXPECTED_INLINE_METHODS


def test_read_only_queries_answer_inline_while_a_job_is_active(tmp_path: Path) -> None:
    started = threading.Event()
    release = threading.Event()
    served: list[str] = []

    class Backend(HeadlessBackend):
        def execute(self, method, params, *, cancellation_token=None, progress=None):
            if method == "library.scan":
                started.set()
                assert release.wait(5)
                return {}
            served.append(method)
            return {"method": method}

    output = io.StringIO()
    server = JsonlServer(Backend(tmp_path), output)
    server.process_line(request("library.scan", {"root": "/somewhere"}))
    assert started.wait(5)
    inline_ids = {method: str(uuid4()) for method in sorted(EXPECTED_INLINE_METHODS)}
    refused_ids = {method: str(uuid4()) for method in EXPECTED_REFUSED_METHODS}
    try:
        for method, request_id in inline_ids.items():
            server.process_line(request(method, request_id=request_id))
        for method, request_id in refused_ids.items():
            server.process_line(request(method, request_id=request_id))
    finally:
        release.set()
        server.close()
    by_id = {item["id"]: item for item in messages(output) if "id" in item}
    for method, request_id in inline_ids.items():
        assert by_id[request_id]["ok"] is True, f"{method} must answer inline during a job"
        assert by_id[request_id]["result"] == {"method": method}
    assert sorted(served) == sorted(EXPECTED_INLINE_METHODS)
    for method, request_id in refused_ids.items():
        assert by_id[request_id]["ok"] is False, f"{method} must stay refused during a job"
        assert by_id[request_id]["error"] == {
            "code": "busy",
            "message": "Another operation is still running",
        }


def test_inline_reads_answer_identically_when_the_host_is_idle(tmp_path: Path) -> None:
    served: list[str] = []

    class Backend(HeadlessBackend):
        def execute(self, method, params, *, cancellation_token=None, progress=None):
            served.append(method)
            return {"method": method}

    output = io.StringIO()
    server = JsonlServer(Backend(tmp_path), output)
    request_ids = {method: str(uuid4()) for method in sorted(EXPECTED_INLINE_METHODS)}
    for method, request_id in request_ids.items():
        server.process_line(request(method, request_id=request_id))
    server.close()
    by_id = {item["id"]: item for item in messages(output) if "id" in item}
    for method, request_id in request_ids.items():
        assert by_id[request_id] == {"id": request_id, "ok": True, "result": {"method": method}}
    assert sorted(served) == sorted(EXPECTED_INLINE_METHODS)


def test_inline_reads_do_not_consume_the_job_slot_or_block_cancellation(tmp_path: Path) -> None:
    started = threading.Event()
    release = threading.Event()

    class Backend(HeadlessBackend):
        def execute(self, method, params, *, cancellation_token=None, progress=None):
            if method == "library.scan":
                started.set()
                assert release.wait(5)
                cancelled = cancellation_token is not None and cancellation_token.is_cancelled
                return {"cancelled": cancelled}
            return {"method": method}

    output = io.StringIO()
    server = JsonlServer(Backend(tmp_path), output)
    job_id, read_id = str(uuid4()), str(uuid4())
    server.process_line(request("library.scan", {"root": "/somewhere"}, job_id))
    assert started.wait(5)
    try:
        server.process_line(request("library.query", request_id=read_id))
        assert next(item for item in messages(output) if item.get("id") == read_id)["ok"] is True
        # An inline read never becomes the active job, so the real job is still cancellable.
        server.process_line(request("cancel", {"jobId": job_id}))
        assert messages(output)[-1]["result"] == {"cancelled": True}
    finally:
        release.set()
        server.close()
    job = next(item for item in messages(output) if item.get("id") == job_id)
    assert job["result"] == {"cancelled": True}


def test_late_prep_cancellation_invalidates_completed_review(tmp_path: Path) -> None:
    from tests.test_headless_backend import tagged_flac

    class LateCancelBackend(HeadlessBackend):
        def execute(self, method, params, *, cancellation_token=None, progress=None):
            result = super().execute(method, params, cancellation_token=cancellation_token, progress=progress)
            if method == "prep.generate" and cancellation_token is not None:
                cancellation_token.cancel()
            return result

    root = tmp_path / "music"
    for index in range(3):
        tagged_flac(root / f"{index}.flac", index)
    backend = LateCancelBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(root)})
    output = io.StringIO()
    server = JsonlServer(backend, output)
    server.process_line(request("prep.generate", {"targetTrackCount": 3}))
    # Wait for completion without using close(), which would cancel before generation.
    with server._lock:
        active = server._active
    if active:
        active[2].join()
    result = messages(output)[-1]
    assert result["ok"] is False
    assert result["error"]["code"] == "cancelled"
    assert backend.review is None
