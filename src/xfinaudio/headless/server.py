"""Bounded JSONL transport with one cancellable worker and stderr-only diagnostics."""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Mapping
from typing import Any, BinaryIO, TextIO
from uuid import UUID

from xfinaudio.headless.backend import BackendError, HeadlessBackend
from xfinaudio.headless.cancellation import JobCancellationToken
from xfinaudio.library.scan_service import ScanCancellationToken

LOGGER = logging.getLogger(__name__)
MAX_LINE_BYTES = 64 * 1024
CANCELLABLE_METHODS = frozenset(
    {"library.scan", "library.rescan", "prep.generate", "prep.select", "loudness.run", "ai.run", "profiles.complete"}
)


class JsonlServer:
    """Trusted Electron main process owns stdin; renderer never accesses this stream."""

    def __init__(self, backend: HeadlessBackend, output: TextIO) -> None:
        self.backend = backend
        self.output = output
        self._lock = threading.RLock()
        self._write_lock = threading.Lock()
        self._close_lock = threading.Lock()
        self._shutdown_complete = False
        self._active: tuple[str, JobCancellationToken, threading.Thread, str] | None = None
        self._closed = False

    def _send(self, message: Mapping[str, Any]) -> None:
        with self._write_lock:
            self.output.write(json.dumps(message, ensure_ascii=False, allow_nan=False) + "\n")
            self.output.flush()

    def _error(self, request_id: str | None, code: str, message: str) -> None:
        self._send({"id": request_id, "ok": False, "error": {"code": code, "message": message}})

    @staticmethod
    def _decode(line: bytes) -> tuple[str, str, dict[str, Any]]:
        try:
            request = json.loads(line)
            if not isinstance(request, dict) or set(request) != {"id", "method", "params"}:
                raise ValueError
            request_id, method, params = request["id"], request["method"], request["params"]
            if not isinstance(request_id, str) or str(UUID(request_id)) != request_id:
                raise ValueError
            if not isinstance(method, str) or not 1 <= len(method) <= 80 or not isinstance(params, dict):
                raise ValueError
            return request_id, method, params
        except (ValueError, TypeError, AttributeError, UnicodeError, RecursionError) as exc:
            raise BackendError("invalid_request", "Expected a UUID request id, command, and parameters object") from exc

    def process_line(self, line: bytes) -> bool:
        """Accept a bounded request; False indicates a requested orderly shutdown."""
        if len(line) > MAX_LINE_BYTES:
            self._error(None, "invalid_request", "Request exceeds the line limit")
            return True
        try:
            request_id, method, params = self._decode(line)
        except BackendError as exc:
            self._error(None, exc.code, str(exc))
            return True
        if method == "shutdown":
            if params:
                self._error(request_id, "invalid_params", "Shutdown takes no parameters")
                return True
            self.close()
            self._send({"id": request_id, "ok": True, "result": {"shutdown": True}})
            return False
        if method == "cancel":
            self._cancel(request_id, params)
            return True
        with self._lock:
            if self._closed:
                self._error(request_id, "closed", "Backend is shutting down")
            elif method in ("track.resolve", "prep.catalog"):
                # Read-only catalog or snapshot lookup; no database or mutable review access.
                self._send(self._execute(request_id, method, params, ScanCancellationToken()))
            elif self._active is not None:
                self._error(request_id, "busy", "Another operation is still running")
            else:
                token = JobCancellationToken()
                thread = threading.Thread(
                    target=self._work, args=(request_id, method, params, token), name="xfinaudio-headless-job"
                )
                self._active = request_id, token, thread, method
                thread.start()
        return True

    def _cancel(self, request_id: str, params: dict[str, Any]) -> None:
        token = None
        with self._lock:
            if self._closed:
                self._error(request_id, "closed", "Backend is shutting down")
                return
            if set(params) != {"jobId"} or not isinstance(params["jobId"], str):
                self._error(request_id, "invalid_params", "Cancel requires a job identity")
                return
            if (
                self._active is not None
                and self._active[0] == params["jobId"]
                and self._active[3] in CANCELLABLE_METHODS
            ):
                token = self._active[1]
                token.request_cancel()
        # A draining hook may wait for a commit that emits progress. Release the
        # publication lock after marking cancellation, before waiting for it.
        if token is not None:
            token.cancel()
        self._send({"id": request_id, "ok": True, "result": {"cancelled": token is not None}})

    def _work(self, request_id: str, method: str, params: dict[str, Any], token: ScanCancellationToken) -> None:
        def progress(data: dict[str, Any]) -> None:
            with self._lock:
                if self._active is not None and self._active[0] == request_id and not token.is_cancelled:
                    self._send({"event": "progress", "jobId": request_id, "data": data})

        response = self._execute(request_id, method, params, token, progress)
        with self._lock:
            # Finalize under the same lock as cancel, so an acknowledged late cancel
            # cannot publish a saveable review after its last domain checkpoint.
            if token.is_cancelled and method in ("prep.generate", "prep.select"):
                self.backend.invalidate_review()
                response = {
                    "id": request_id,
                    "ok": False,
                    "error": {"code": "cancelled", "message": "Preparation cancelled"},
                }
            if token.is_cancelled and method == "profiles.complete" and response.get("ok"):
                self.backend.profiles.state = "cancelled"
                response["result"] = {**response["result"], "cancelled": True, "status": self.backend.profiles.status()}
            if token.is_cancelled and method == "ai.run":
                self.backend.invalidate_optional_ai()
                response = {"id": request_id, "ok": True, "result": {"cancelled": True, "result": None}}
            self._active = None
            self._send(response)

    def _execute(
        self, request_id: str, method: str, params: dict[str, Any], token: ScanCancellationToken, progress=None
    ) -> dict[str, Any]:
        try:
            result = self.backend.execute(method, params, cancellation_token=token, progress=progress)
            return {"id": request_id, "ok": True, "result": result}
        except BackendError as exc:
            return {"id": request_id, "ok": False, "error": {"code": exc.code, "message": str(exc)}}
        except Exception:
            LOGGER.exception("Headless command failed: %s", method)
            return {
                "id": request_id,
                "ok": False,
                "error": {"code": "internal_error", "message": "The operation failed; check local diagnostics"},
            }

    def close(self) -> None:
        """Drain the active job, then owned backend resources, exactly once."""
        with self._close_lock:
            if self._shutdown_complete:
                return
            with self._lock:
                self._closed = True
                active = self._active
                if active is not None and active[3] in CANCELLABLE_METHODS:
                    active[1].request_cancel()
            if active is not None:
                if active[3] in CANCELLABLE_METHODS:
                    active[1].cancel()
                active[2].join()
            shutdown = getattr(self.backend, "shutdown", None)
            if callable(shutdown):
                shutdown()
            self._shutdown_complete = True

    def run(self, source: BinaryIO) -> None:
        try:
            while line := source.readline(MAX_LINE_BYTES + 1):
                if len(line) > MAX_LINE_BYTES:
                    self._error(None, "invalid_request", "Request exceeds the line limit")
                    while not line.endswith(b"\n"):
                        line = source.readline(MAX_LINE_BYTES + 1)
                        if not line:
                            break
                    continue
                if not self.process_line(line):
                    break
        finally:
            self.close()
