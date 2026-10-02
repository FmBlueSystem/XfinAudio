"""Read-only completion uses original adapters and current repository profiles."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tests.test_headless_backend import tagged_flac
from xfinaudio.audio.danceability import DanceabilityProfile
from xfinaudio.audio.spectral_profile import CURRENT_ANALYSIS_VERSION, EdgeSpectralProfile, SpectralProfile
from xfinaudio.headless.backend import BackendError, HeadlessBackend
from xfinaudio.library.scan_service import ScanCancellationToken


def spectral(version=CURRENT_ANALYSIS_VERSION):
    return SpectralProfile(
        red_ratio=0.8,
        green_ratio=0.15,
        blue_ratio=0.05,
        dominant_color="RED",
        centroid_hz=1000,
        rolloff_hz=2000,
        analysis_version=version,
    )


def danceability():
    return DanceabilityProfile(score=0.8, pulse_clarity=0.8, tempo_confidence=0.8, percussive_ratio=0.8)


def library(tmp_path: Path, count=2):
    root = tmp_path / "music"
    for index in range(count):
        tagged_flac(root / f"{index}.flac", index)
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(root)})
    return backend, root


def engines(monkeypatch, *, failure=None, action=None):
    from xfinaudio.headless import profiles

    calls = []
    monkeypatch.setattr(profiles, "dependencies_available", lambda: True)
    for stage, name, profile in (
        ("spectral", "LibrosaSpectralAnalyzer", spectral()),
        ("danceability", "LibrosaDanceabilityAnalyzer", danceability()),
        ("edge", "LibrosaEdgeSpectralAnalyzer", EdgeSpectralProfile(intro=spectral(), outro=spectral())),
    ):

        def analyze(self, path, stage=stage, profile=profile):
            calls.append((stage, path))
            if action:
                action(stage, path)
            if failure == "raise":
                raise RuntimeError(f"Secret private path {path}")
            return None if failure else profile

        monkeypatch.setattr(getattr(profiles, name), "analyze", analyze)
    return calls


def test_empty_status_and_completion_do_not_probe_dependencies(tmp_path, monkeypatch):
    from xfinaudio.headless import profiles

    monkeypatch.setattr(profiles, "dependencies_available", lambda: pytest.fail("Empty library probed engines"))
    backend = HeadlessBackend(tmp_path)
    status = backend.execute("profiles.status", {})
    assert status == {
        "state": "idle",
        "totalTracks": 0,
        "readyCount": 0,
        "spectralReadyCount": 0,
        "danceabilityReadyCount": 0,
        "edgeReadyCount": 0,
        "pendingCount": 0,
        "failedCount": 0,
    }
    result = backend.execute("profiles.complete", {})
    assert result["status"] == status and result["cancelled"] is False and result["tracks"] == []


def test_original_stage_order_readonly_persistence_and_restart_cache(tmp_path, monkeypatch):
    backend, root = library(tmp_path)
    calls = engines(monkeypatch)
    before = {p: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns) for p in root.iterdir()}
    progress = []
    result = backend.execute("profiles.complete", {}, progress=progress.append)
    assert [stage for stage, _ in calls] == ["spectral"] * 2 + ["danceability"] * 2 + ["edge"] * 2
    assert result["status"] == {
        "state": "complete",
        "totalTracks": 2,
        "readyCount": 2,
        "spectralReadyCount": 2,
        "danceabilityReadyCount": 2,
        "edgeReadyCount": 2,
        "pendingCount": 0,
        "failedCount": 0,
    }
    assert result["cancelled"] is False
    assert all(event["phase"] == "profiles" for event in progress)
    assert str(root) not in json.dumps(result) + json.dumps(progress)
    restarted = HeadlessBackend(tmp_path / "data")
    assert restarted.execute("profiles.complete", {})["status"]["readyCount"] == 2
    assert len(calls) == 6
    assert all(
        (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns) == state for p, state in before.items()
    )
    for strategy in ("same_color", "same_color_energy"):
        review = restarted.execute("prep.generate", {"targetTrackCount": 2, "strategy": strategy})
        assert len(review["tracks"]) == 2


def test_stale_version_changed_and_symlink_sources_are_not_reused(tmp_path, monkeypatch):
    backend, root = library(tmp_path)
    calls = engines(monkeypatch)
    for record in backend._records():
        backend.repository.update_spectral_profile(record.path, spectral(1))
    backend.execute("profiles.complete", {})
    assert len(calls) == 6
    path = root / "0.flac"
    path.write_bytes(path.read_bytes() + b"changed")
    assert backend.execute("profiles.status", {})["readyCount"] == 1
    assert backend._records()[0].spectral_profile is None
    backend.execute("profiles.complete", {})
    assert len(calls) == 9
    outside = tmp_path / "outside.flac"
    tagged_flac(outside)
    path.unlink()
    path.symlink_to(outside)
    assert backend.execute("profiles.status", {})["readyCount"] == 1
    backend.execute("profiles.complete", {})
    assert len(calls) == 9


def test_cancel_drops_late_result_and_prevents_following_stages(tmp_path, monkeypatch):
    backend, _ = library(tmp_path, 1)
    token = ScanCancellationToken()
    calls = engines(monkeypatch, action=lambda stage, path: token.cancel())
    result = backend.execute("profiles.complete", {}, cancellation_token=token)
    assert result["cancelled"] and result["status"]["state"] == "cancelled"
    assert calls[0][0] == "spectral" and len(calls) == 1
    assert backend.repository.list_display_tracks()[0].spectral_profile is None
    engines(monkeypatch)
    assert backend.execute("profiles.complete", {})["status"]["readyCount"] == 1


@pytest.mark.parametrize("failure", ["none", "raise"])
def test_silent_unreadable_or_failed_profiles_are_honest_and_retryable(tmp_path, monkeypatch, failure):
    backend, root = library(tmp_path)
    calls = engines(monkeypatch, failure=failure)
    result = backend.execute("profiles.complete", {})
    assert result["status"]["state"] == "partial"
    assert result["status"]["readyCount"] == 0 and result["status"]["failedCount"] == 2
    assert len(calls) == 6 and str(root) not in json.dumps(result)
    engines(monkeypatch)
    assert backend.execute("profiles.complete", {})["status"]["state"] == "complete"


def test_dependencies_unavailable_never_fabricates_profiles(tmp_path, monkeypatch):
    from xfinaudio.headless import profiles

    backend, _ = library(tmp_path)
    monkeypatch.setattr(profiles, "dependencies_available", lambda: False)
    result = backend.execute("profiles.complete", {})
    assert result["status"]["state"] == "unavailable" and result["status"]["readyCount"] == 0
    assert result["status"]["pendingCount"] == 2


def test_changed_during_analysis_and_failed_persistence_never_count_success(tmp_path, monkeypatch):
    backend, _ = library(tmp_path, 1)
    engines(monkeypatch, action=lambda stage, path: path.write_bytes(path.read_bytes() + b"changed"))
    assert backend.execute("profiles.complete", {})["status"]["readyCount"] == 0
    engines(monkeypatch)
    monkeypatch.setattr(backend.repository, "update_spectral_profile", lambda *args, **kwargs: False)
    status = backend.execute("profiles.complete", {})["status"]
    assert status["spectralReadyCount"] == 0 and status["failedCount"] == 1


@pytest.mark.parametrize(
    "method,params", [("profiles.complete", {"root": "/secret"}), ("profiles.status", {"force": True})]
)
def test_completion_rejects_unexpected_fields(tmp_path, method, params):
    with pytest.raises(BackendError) as caught:
        HeadlessBackend(tmp_path).execute(method, params)
    assert caught.value.code == "invalid_params"


def test_profile_preferences_preserve_unrelated_settings_and_reject_stale_revision(tmp_path):
    backend = HeadlessBackend(tmp_path)
    initial = backend.execute("profiles.settings.get", {})
    assert initial["spectralCohesion"] == 0.5
    other = backend.execute("settings.get", {})
    backend.execute("settings.update", {"revision": other["revision"], "previewVolume": 0.2, "watchLibrary": False})
    with pytest.raises(BackendError) as error:
        backend.execute("profiles.settings.update", {**initial, "spectralCohesion": 0.8})
    assert error.value.code == "stale_settings"
    fresh = backend.execute("profiles.settings.get", {})
    updated = backend.execute("profiles.settings.update", {**fresh, "spectralCohesion": 0.8})
    assert updated["spectralCohesion"] == 0.8 and updated["revision"] != fresh["revision"]
    restored = HeadlessBackend(tmp_path)
    assert restored.preferences.spectral_cohesion() == 0.8
    assert restored.execute("settings.get", {})["previewVolume"] == 0.2
    assert restored.execute("settings.get", {})["watchLibrary"] is False


@pytest.mark.parametrize("value", [True, False, -1, 1.01, float("inf"), float("nan"), "0.5", None])
def test_profile_preference_rejects_invalid_value(tmp_path, value):
    backend = HeadlessBackend(tmp_path)
    settings = backend.execute("profiles.settings.get", {})
    with pytest.raises(BackendError) as error:
        backend.execute("profiles.settings.update", {**settings, "spectralCohesion": value})
    assert error.value.code == "invalid_params"
    assert backend.execute("profiles.settings.get", {}) == settings


def test_cohesion_reaches_original_prep_scoring_and_invalidates_contexts(tmp_path, monkeypatch):
    from xfinaudio.recommendation import prep_copilot

    backend, _ = library(tmp_path)
    engines(monkeypatch)
    backend.execute("profiles.complete", {})
    calls = []
    original = prep_copilot.recommend_playlist

    def recommend(*args, **kwargs):
        calls.append(kwargs.get("spectral_cohesion"))
        return original(*args, **kwargs)

    monkeypatch.setattr(prep_copilot, "recommend_playlist", recommend)
    review = backend.execute("prep.generate", {"targetTrackCount": 2})
    assert calls == [0.5, 0.5, 0.5]
    live = backend.execute("live.open", {"reviewId": review["reviewId"]})
    settings = backend.execute("profiles.settings.get", {})
    backend.execute("profiles.settings.update", {**settings, "spectralCohesion": 0.75})
    assert backend.plan is None and backend.review is None and backend.live.session is None
    with pytest.raises(BackendError):
        backend.execute("live.status", {"sessionId": live["sessionId"]})
    backend.execute("prep.generate", {"targetTrackCount": 2})
    assert calls[-3:] == [0.75] * 3


def test_live_ranking_uses_current_spectral_cohesion(tmp_path, monkeypatch):
    from xfinaudio.headless import live_session

    backend, _ = library(tmp_path, 3)
    engines(monkeypatch)
    backend.execute("profiles.complete", {})
    review = backend.execute("prep.generate", {"targetTrackCount": 3})
    original = live_session.rank_live_candidates
    calls = []

    def rank(*args, **kwargs):
        calls.append(kwargs.get("spectral_cohesion"))
        return original(*args, **kwargs)

    monkeypatch.setattr(live_session, "rank_live_candidates", rank)
    backend.execute("live.open", {"reviewId": review["reviewId"]})
    assert calls and all(value == 0.5 for value in calls)


def test_jsonl_cancel_drains_analysis_and_never_publishes_late_result(tmp_path, monkeypatch):
    import io
    import threading
    from uuid import uuid4

    from tests.test_headless_protocol import messages, request
    from xfinaudio.headless.server import JsonlServer

    backend, _ = library(tmp_path, 1)
    entered, release = threading.Event(), threading.Event()

    def analyze(stage, path):
        entered.set()
        assert release.wait(5)

    calls = engines(monkeypatch, action=analyze)
    output = io.StringIO()
    server = JsonlServer(backend, output)
    job_id = str(uuid4())
    server.process_line(request("profiles.complete", request_id=job_id))
    assert entered.wait(5)
    server.process_line(request("cancel", {"jobId": job_id}))
    server.process_line(request("profiles.complete"))
    responses = messages(output)
    assert responses[-2]["result"] == {"cancelled": True}
    assert responses[-1]["error"]["code"] == "busy"
    closing = threading.Thread(target=server.close)
    closing.start()
    assert closing.is_alive()
    release.set()
    closing.join(5)
    assert not closing.is_alive()
    result = next(item for item in messages(output) if item.get("id") == job_id)
    assert result["result"]["cancelled"] is True
    assert result["result"]["status"]["readyCount"] == 0
    assert len(calls) == 1
    assert backend.repository.list_display_tracks()[0].spectral_profile is None


def test_real_original_engines_generate_all_profiles_without_source_writes(tmp_path):
    import importlib.util
    import sys

    if importlib.util.find_spec("librosa") is None or importlib.util.find_spec("soundfile") is None:
        pytest.skip("Original read-only analysis dependencies are not installed in this test interpreter")
    import numpy as np
    import soundfile as sf
    from mutagen.flac import FLAC

    qt_before = {module for module in sys.modules if module.startswith(("PySide6", "xfinaudio.desktop"))}
    rate = 22050
    time = np.arange(rate * 70, dtype=np.float32) / rate
    pulse = 0.2 + 0.8 * np.exp(-np.mod(time, 0.5) * 15)
    samples = (pulse * (np.sin(2 * np.pi * 120 * time) + 0.2 * np.sin(2 * np.pi * 240 * time))).astype(np.float32) * 0.5
    root = tmp_path / "audible"
    root.mkdir()
    for index in range(3):
        path = root / f"audible-{index}.flac"
        sf.write(path, samples, rate, subtype="PCM_16")
        tags = FLAC(path)
        tags.update(
            {"title": f"Audible {index}", "artist": "Synthetic", "bpm": "120", "initialkey": "8A", "energylevel": "5"}
        )
        tags.save()
    before = {p: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns) for p in root.iterdir()}
    backend = HeadlessBackend(tmp_path / "data")
    assert backend.execute("library.scan", {"root": str(root)})["completeCount"] == 3
    status = backend.execute("profiles.complete", {})["status"]
    assert status["state"] == "complete" and status["readyCount"] == 3
    for strategy in ("same_color", "same_color_energy"):
        assert len(backend.execute("prep.generate", {"targetTrackCount": 3, "strategy": strategy})["tracks"]) == 3
    assert all(
        (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns) == state for p, state in before.items()
    )
    assert {module for module in sys.modules if module.startswith(("PySide6", "xfinaudio.desktop"))} == qt_before


def test_source_change_inside_repository_commit_cannot_rebind_stale_profile(tmp_path, monkeypatch):
    backend, root = library(tmp_path, 1)
    engines(monkeypatch)
    original = backend.repository.update_spectral_profile

    def changed_commit(path, profile, **kwargs):
        source = Path(path)
        source.write_bytes(source.read_bytes() + b"changed during commit")
        return original(path, profile, **kwargs)

    monkeypatch.setattr(backend.repository, "update_spectral_profile", changed_commit)
    status = backend.execute("profiles.complete", {})["status"]
    assert status["spectralReadyCount"] == 0
    assert backend.repository.list_display_tracks()[0].spectral_profile is None
    assert status["failedCount"] == 1 and (root / "0.flac").exists()


def test_late_cancel_between_backend_result_and_server_publication_is_truthful(tmp_path):
    import io
    import threading
    from uuid import uuid4

    from tests.test_headless_protocol import messages, request
    from xfinaudio.headless.server import JsonlServer

    backend, _ = library(tmp_path, 1)
    ready, release = threading.Event(), threading.Event()

    class Server(JsonlServer):
        def _execute(self, request_id, method, params, token, progress=None):
            response = {
                "id": request_id,
                "ok": True,
                "result": {**backend._library(), "cancelled": False, "status": backend.profiles.status()},
            }
            ready.set()
            assert release.wait(5)
            return response

    output = io.StringIO()
    server = Server(backend, output)
    job = str(uuid4())
    server.process_line(request("profiles.complete", request_id=job))
    assert ready.wait(5)
    server.process_line(request("cancel", {"jobId": job}))
    release.set()
    server.close()
    result = next(item for item in messages(output) if item.get("id") == job)["result"]
    assert result["cancelled"] is True and result["status"]["state"] == "cancelled"


def test_real_silent_audio_is_not_reported_as_completed(tmp_path):
    pytest.importorskip("soundfile")
    pytest.importorskip("librosa")
    import numpy as np
    import soundfile as sf

    root = tmp_path / "silent"
    root.mkdir()
    path = root / "silence.flac"
    sf.write(path, np.zeros(22050 * 70, dtype=np.float32), 22050)
    before = hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(root)})
    status = backend.execute("profiles.complete", {})["status"]
    assert status["state"] == "partial" and status["failedCount"] == status["pendingCount"] == 1
    assert status["spectralReadyCount"] == status["danceabilityReadyCount"] == status["edgeReadyCount"] == 0
    assert (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns) == before
