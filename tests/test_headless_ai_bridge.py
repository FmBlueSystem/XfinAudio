"""Trusted JSONL routes use the optional facade without real provider traffic."""

import io
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from uuid import uuid4

from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.server import JsonlServer


def test_baseline_scan_and_loudness_invalidation_do_not_initialize_optional_ai(tmp_path):
    script = r"""
import importlib.abc, sys
from pathlib import Path
class Firewall(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('PySide6', 'xfinaudio.desktop', 'xfinaudio.ai', 'xfinaudio.headless.optional_ai')):
            raise AssertionError(fullname)
sys.meta_path.insert(0, Firewall())
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.common import BackendError
root = Path(sys.argv[1])
music = root / 'music'
music.mkdir()
backend = HeadlessBackend(root / 'data')
backend.execute('library.scan', {'root': str(music)})
backend.execute('library.rescan', {})
try:
    backend.execute('loudness.run', {'previewId': 'invalid', 'confirmed': True})
except BackendError:
    pass
else:
    raise AssertionError('Invalid loudness run unexpectedly succeeded')
backend.invalidate_optional_ai()
backend.shutdown()
assert backend._optional_ai is None
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
    )
    assert completed.returncode == 0, completed.stderr


def test_optional_ai_is_initialized_once_and_invalidated_only_when_present(tmp_path):
    backend = HeadlessBackend(tmp_path / "data")
    assert backend._optional_ai is None
    backend.invalidate_optional_ai()
    assert backend._optional_ai is None
    facade = backend.optional_ai
    assert backend.optional_ai is facade
    preview = backend.execute(
        "ai.prepare", {"surface": "connection", "request": "Reply with OK. XfinAudio connection test.", "context": {}}
    )
    assert facade.preview is not None and facade.preview.id == preview["previewId"]
    backend.invalidate_optional_ai()
    assert backend.optional_ai is facade and facade.preview is None


def configured(tmp_path):
    music = tmp_path / "music"
    shutil.copytree(Path(__file__).resolve().parents[1] / "desktop-electron/tests/fixtures/music", music)
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(music)})
    status = backend.execute("ai.status", {})
    status = backend.execute("ai.settings.update", {"revision": status["revision"], "enabled": True})
    credential = tmp_path / "dummy.env"
    credential.write_text("NAN_API_KEY=dummy-test-only\n")
    backend.execute("ai.credential.set", {"revision": status["revision"], "path": str(credential)})
    calls = []

    def transport(request, *, timeout):
        calls.append(request.full_url)
        return io.BytesIO(json.dumps({"choices": [{"message": {"content": '{"genre":"House"}'}}]}).encode())

    backend.optional_ai.transport = transport
    return backend, calls


def test_backend_routes_config_prepare_run_and_readonly_apply(tmp_path):
    backend, calls = configured(tmp_path)
    preview = backend.execute("ai.prepare", {"surface": "library", "request": "House", "context": {}})
    assert calls == []
    result = backend.execute("ai.run", {"previewId": preview["previewId"], "confirmed": True})
    assert len(calls) == 1 and not result["cancelled"]
    applied = backend.execute("ai.apply", {"resultId": result["result"]["resultId"]})
    assert applied["surface"] == "library" and len(applied["data"]["trackIds"]) == 8
    assert backend.playlists.list_summaries() == []


def test_acknowledged_late_cancel_never_publishes_or_retains_ai_result(tmp_path):
    backend, calls = configured(tmp_path)
    preview = backend.execute("ai.prepare", {"surface": "library", "request": "House", "context": {}})
    output = io.StringIO()
    server = JsonlServer(backend, output)
    completed = threading.Event()
    release = threading.Event()
    original = server._execute

    def paused(*args, **kwargs):
        value = original(*args, **kwargs)
        completed.set()
        assert release.wait(3)
        return value

    server._execute = paused
    job = str(uuid4())
    cancel = str(uuid4())
    server.process_line(
        json.dumps(
            {"id": job, "method": "ai.run", "params": {"previewId": preview["previewId"], "confirmed": True}}
        ).encode()
    )
    assert completed.wait(3)
    assert backend.optional_ai.results
    server.process_line(json.dumps({"id": cancel, "method": "cancel", "params": {"jobId": job}}).encode())
    release.set()
    server.close()
    replies = {value["id"]: value for value in map(json.loads, output.getvalue().splitlines()) if "id" in value}
    assert replies[cancel]["result"] == {"cancelled": True}
    assert replies[job]["result"] == {"cancelled": True, "result": None}
    assert not backend.optional_ai.results and len(calls) == 1
