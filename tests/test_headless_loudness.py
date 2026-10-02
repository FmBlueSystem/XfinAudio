"""Loudness scope/confirmation boundaries use real completion and tag code on owned copies."""

import shutil
import threading
from pathlib import Path

import pytest
from mutagen.flac import FLAC

import xfinaudio.headless.loudness as loudness_module
from xfinaudio.audio.loudness import LoudnessProfile, LoudnessStatus
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.cancellation import JobCancellationToken
from xfinaudio.headless.common import BackendError
from xfinaudio.headless.loudness import Engine

FIXTURES = Path(__file__).resolve().parents[1] / "desktop-electron/tests/fixtures/music"


class Analyzer:
    calls = 0

    def analyze(self, path, *, duration_seconds):
        self.calls += 1
        return LoudnessProfile(
            lufs_integrated=-11,
            loudness_range_lra=4,
            true_peak_dbtp=-2,
            status=LoudnessStatus.MEASURED,
            engine_fingerprint="fixture",
        )

    def cancel(self):
        pass

    def shutdown(self):
        pass


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    root = tmp_path / "music"
    root.mkdir()
    for i, source in enumerate(sorted(FIXTURES.glob("*.flac"))[:2]):
        shutil.copyfile(source, root / f"{i}.flac")
    analyzer = Analyzer()
    monkeypatch.setattr(loudness_module, "create_engine", lambda: Engine(analyzer, "fixture"))
    backend = HeadlessBackend(tmp_path / "data")
    tracks = backend.execute("library.scan", {"root": str(root)})["tracks"]
    return backend, tracks, root, analyzer


def test_status_preview_and_cancelled_confirmation_never_mutate_audio(fixture):
    backend, tracks, root, analyzer = fixture
    before = {p: p.read_bytes() for p in root.iterdir()}
    status = backend.execute("loudness.status", {})
    assert status["available"] and status["enabled"]
    assert status["reason"] == "ready" and status["totalTracks"] == 2
    assert all(item["state"] == "unmeasured" for item in status["tracks"])
    preview = backend.execute("loudness.preview", {"trackIds": [tracks[0]["id"]], "force": False})
    assert preview["trackCount"] == 1 and preview["replaceComments"] is True
    assert str(root) not in str(preview)
    with pytest.raises(BackendError):
        backend.execute("loudness.run", {"previewId": preview["previewId"], "confirmed": False})
    assert analyzer.calls == 0
    assert {p: p.read_bytes() for p in root.iterdir()} == before


def test_confirmed_scope_runs_original_completion_tags_cache_and_idempotent_receipt(fixture):
    backend, tracks, root, analyzer = fixture
    untouched = (root / "1.flac").read_bytes()
    before = (root / "0.flac").read_bytes()
    preview = backend.execute("loudness.preview", {"trackIds": [tracks[0]["id"]], "force": False})
    confirmation = backend.execute("loudness.confirmation", {"previewId": preview["previewId"]})
    assert confirmation["trackCount"] == 1
    progress = []
    result = backend.execute(
        "loudness.run", {"previewId": preview["previewId"], "confirmed": True}, progress=progress.append
    )
    assert result["changedCount"] == result["backupCount"] == 1
    assert result["failureCount"] == 0 and not result["cancelled"]
    assert analyzer.calls == 1 and progress
    assert (root / "1.flac").read_bytes() == untouched
    backups = list((backend.data_dir / "loudness-backups").rglob("*.bak"))
    assert len(backups) == 1 and backups[0].read_bytes() == before
    assert result["status"]["tracks"][0]["complete"] is True
    assert backend.execute("loudness.run", {"previewId": preview["previewId"], "confirmed": True}) == result
    assert analyzer.calls == 1


@pytest.mark.parametrize("change", ["settings", "source", "scan"])
def test_preview_rejects_changed_source_policy_or_context(fixture, change):
    backend, tracks, root, analyzer = fixture
    preview = backend.execute("loudness.preview", {"trackIds": [tracks[0]["id"]], "force": False})
    if change == "settings":
        s = backend.preferences.get_loudness()
        backend.preferences.update_loudness({**s, "targetLufs": -12})
    elif change == "source":
        tags = FLAC(root / "0.flac")
        tags["COMMENT"] = ["edited elsewhere"]
        tags.save()
    else:
        backend.execute("library.rescan", {})
    with pytest.raises(BackendError):
        backend.execute("loudness.run", {"previewId": preview["previewId"], "confirmed": True})
    assert analyzer.calls == 0


@pytest.mark.parametrize(
    "params",
    [
        {"trackIds": [], "force": False},
        {"trackIds": ["a" * 64], "force": False},
        {"trackIds": [], "force": False, "root": "/private"},
        {"trackIds": [], "force": 1},
    ],
)
def test_invalid_scope_never_reaches_engine(fixture, params):
    backend, _, _, analyzer = fixture
    with pytest.raises(BackendError):
        backend.execute("loudness.preview", params)
    assert analyzer.calls == 0


def test_disabled_or_missing_engine_is_truthful_and_cannot_preview(fixture, monkeypatch):
    backend, tracks, _, _ = fixture
    s = backend.preferences.get_loudness()
    backend.execute("loudness.settings.update", {**s, "enabled": False})
    with pytest.raises(BackendError, match="disabled"):
        backend.execute("loudness.preview", {"trackIds": [tracks[0]["id"]], "force": False})
    monkeypatch.setattr(loudness_module, "create_engine", lambda: None)
    other = HeadlessBackend(backend.data_dir)
    assert other.execute("loudness.status", {})["reason"] == "missing_engine"
    assert not other.execute("loudness.status", {})["available"]


def test_cancellation_reaches_original_service_and_drains_analysis_without_tag_write(fixture):
    backend, tracks, root, analyzer = fixture
    started = threading.Event()
    stopped = threading.Event()

    def analyze(path, *, duration_seconds):
        started.set()
        assert stopped.wait(3)
        return LoudnessProfile(
            lufs_integrated=None,
            loudness_range_lra=None,
            true_peak_dbtp=None,
            status=LoudnessStatus.TRANSIENT_FAILURE,
            engine_fingerprint="fixture",
        )

    analyzer.analyze = analyze
    analyzer.cancel = stopped.set
    preview = backend.execute("loudness.preview", {"trackIds": [tracks[0]["id"]], "force": False})
    token = JobCancellationToken()
    result = []
    before = (root / "0.flac").read_bytes()
    thread = threading.Thread(
        target=lambda: result.append(
            backend.execute(
                "loudness.run", {"previewId": preview["previewId"], "confirmed": True}, cancellation_token=token
            )
        )
    )
    thread.start()
    assert started.wait(3)
    token.cancel()
    thread.join(3)
    assert not thread.is_alive() and result[0]["cancelled"]
    assert (root / "0.flac").read_bytes() == before


def test_cache_replay_and_single_track_reanalysis_do_not_create_redundant_backups(fixture):
    backend, tracks, _, analyzer = fixture
    scope = {"trackIds": [tracks[0]["id"]], "force": False}
    preview = backend.execute("loudness.preview", scope)
    backend.execute("loudness.run", {"previewId": preview["previewId"], "confirmed": True})
    again = backend.execute("loudness.preview", scope)
    replay = backend.execute("loudness.run", {"previewId": again["previewId"], "confirmed": True})
    assert analyzer.calls == 1 and replay["backupCount"] == 0 and replay["unchangedCount"] == 1
    force = backend.execute("loudness.preview", {**scope, "force": True})
    result = backend.execute("loudness.run", {"previewId": force["previewId"], "confirmed": True})
    assert analyzer.calls == 2 and result["backupCount"] == 0 and result["unchangedCount"] == 1


def test_cache_failure_after_a_changed_write_still_returns_counts_and_backup_warning(fixture, monkeypatch):
    backend, tracks, root, _ = fixture
    before = (root / "0.flac").read_bytes()
    preview = backend.execute("loudness.preview", {"trackIds": [tracks[0]["id"]], "force": False})

    def broken_cache(*args, **kwargs):
        raise OSError("private path cache unavailable")

    monkeypatch.setattr(backend.repository, "update_loudness_profile", broken_cache)
    result = backend.execute("loudness.run", {"previewId": preview["previewId"], "confirmed": True})
    assert result["changedCount"] == result["backupCount"] == 1
    assert result["warning"] and "private path" not in result["warning"]
    assert "parciales" in result["warning"]
    assert list((backend.data_dir / "loudness-backups").rglob("*.bak"))[0].read_bytes() == before


def test_source_changed_before_preview_requires_rescan_instead_of_using_stale_duration(fixture):
    backend, tracks, root, analyzer = fixture
    tags = FLAC(root / "0.flac")
    tags["COMMENT"] = ["changed after scan"]
    tags.save()
    with pytest.raises(BackendError):
        backend.execute("loudness.preview", {"trackIds": [tracks[0]["id"]], "force": False})
    assert analyzer.calls == 0


def test_external_change_hides_historical_measured_values_until_rescan(fixture):
    backend, tracks, root, _ = fixture
    preview = backend.execute("loudness.preview", {"trackIds": [tracks[0]["id"]], "force": False})
    backend.execute("loudness.run", {"previewId": preview["previewId"], "confirmed": True})
    tags = FLAC(root / "0.flac")
    tags["COMMENT"] = ["external"]
    tags.save()
    item = next(
        item for item in backend.execute("loudness.status", {})["tracks"] if item["track"]["id"] == tracks[0]["id"]
    )
    assert item["state"] == "unmeasured" and item["complete"] is False


def test_owned_tag_write_suppression_progress_contains_only_scoped_track_ids(fixture):
    backend, tracks, _, _ = fixture
    preview = backend.execute("loudness.preview", {"trackIds": [tracks[0]["id"]], "force": False})
    progress = []
    backend.execute("loudness.run", {"previewId": preview["previewId"], "confirmed": True}, progress=progress.append)
    suppress = [value for value in progress if value["phase"] == "loudness_write"]
    assert suppress == [{"phase": "loudness_write", "trackIds": [tracks[0]["id"]]}]


def test_cancellation_waits_for_started_tag_commit_before_returning_receipt(fixture, monkeypatch):
    from xfinaudio.headless.loudness_write import BoundLoudnessWriter

    backend, tracks, _, _ = fixture
    entered = threading.Event()
    release = threading.Event()
    cancelled = threading.Event()
    original = BoundLoudnessWriter.__call__

    def hold(self, path, profile):
        entered.set()
        assert release.wait(3)
        return original(self, path, profile)

    monkeypatch.setattr(BoundLoudnessWriter, "__call__", hold)
    preview = backend.execute("loudness.preview", {"trackIds": [tracks[0]["id"]], "force": False})
    token = JobCancellationToken()
    result = []
    thread = threading.Thread(
        target=lambda: result.append(
            backend.execute(
                "loudness.run", {"previewId": preview["previewId"], "confirmed": True}, cancellation_token=token
            )
        )
    )
    thread.start()
    assert entered.wait(3)
    cancel = threading.Thread(target=lambda: (token.cancel(), cancelled.set()))
    cancel.start()
    assert not cancelled.wait(0.05)
    release.set()
    thread.join(3)
    cancel.join(3)
    assert (
        cancelled.is_set()
        and result[0]["cancelled"]
        and result[0]["changedCount"] == 1
        and result[0]["backupCount"] == 1
    )


def test_terminal_settings_failure_does_not_hide_completed_writes(fixture, monkeypatch):
    backend, tracks, _, _ = fixture
    preview = backend.execute("loudness.preview", {"trackIds": [tracks[0]["id"]], "force": False})
    original = backend.preferences.get_loudness
    calls = 0

    def fail_late():
        nonlocal calls
        calls += 1
        if calls >= 3:
            raise BackendError("settings_unavailable", "not public technical details")
        return original()

    monkeypatch.setattr(backend.preferences, "get_loudness", fail_late)
    result = backend.execute("loudness.run", {"previewId": preview["previewId"], "confirmed": True})
    assert result["changedCount"] == result["backupCount"] == 1
    assert result["warning"] and "technical" not in result["warning"]


def test_engine_composition_uses_original_adapter_and_preflight(monkeypatch):
    import xfinaudio.headless.loudness as module

    calls = []

    class Adapter:
        def __init__(self, executable, *, engine_fingerprint):
            calls.append((executable, engine_fingerprint))

        def preflight(self):
            calls.append("preflight")

    monkeypatch.setattr(module, "resolve_ffmpeg", lambda: Path("/trusted/ffmpeg"))
    monkeypatch.setattr(module, "probe_engine_fingerprint", lambda path: "fingerprint")
    monkeypatch.setattr(module, "FfmpegLoudnessAdapter", Adapter)
    assert module.create_engine().fingerprint == "fingerprint"
    assert calls == [(Path("/trusted/ffmpeg"), "fingerprint"), "preflight"]
    monkeypatch.setattr(module, "probe_engine_fingerprint", lambda path: None)
    with pytest.raises(OSError):
        module.create_engine()
    monkeypatch.setattr(module, "resolve_ffmpeg", lambda: None)
    assert module.create_engine() is None


def test_failed_engine_preflight_is_truthful_and_does_not_escape_paths(fixture, monkeypatch):
    backend, _, _, _ = fixture

    def fail():
        raise RuntimeError("/private/engine unavailable")

    monkeypatch.setattr(loudness_module, "create_engine", fail)
    status = backend.execute("loudness.status", {})
    assert not status["available"] and status["reason"] == "failed_engine"
    assert "/private" not in str(status)
