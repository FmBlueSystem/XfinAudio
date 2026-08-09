"""Tests for progressive danceability profile completion."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from xfinaudio.audio.danceability import CURRENT_DANCEABILITY_VERSION, DanceabilityProfile
from xfinaudio.desktop.danceability_completion_worker import DanceabilityCompletionWorker
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import ScanCancellationToken

_EXISTING_APP = QApplication.instance()
_APP: QApplication = _EXISTING_APP if isinstance(_EXISTING_APP, QApplication) else QApplication([])


def ensure_app() -> None:
    _ = _APP


def _profile(*, analysis_version: int = CURRENT_DANCEABILITY_VERSION) -> DanceabilityProfile:
    return DanceabilityProfile(
        score=0.72,
        pulse_clarity=0.8,
        tempo_confidence=0.9,
        percussive_ratio=0.6,
        analysis_version=analysis_version,
    )


class _FakeAnalyzer:
    def __init__(self, profile: DanceabilityProfile) -> None:
        self.profile = profile
        self.calls: list[Path] = []

    def analyze(self, path: Path) -> DanceabilityProfile:
        self.calls.append(path)
        return self.profile


class _FakeRepository:
    def __init__(self, profiles: dict[str, DanceabilityProfile] | None = None) -> None:
        self.updated: dict[str, DanceabilityProfile] = {}
        self._cache = profiles or {}

    def load_danceability_profile_cache(self, paths: list[str]) -> dict[str, tuple[int, int, DanceabilityProfile]]:
        return {path: (0, 0, self._cache[path]) for path in paths if path in self._cache}

    def update_danceability_profile(self, path: str, profile: DanceabilityProfile) -> bool:
        self.updated[path] = profile
        return True


def _wait_for_worker(worker: DanceabilityCompletionWorker, timeout_ms: int = 5000) -> None:
    loop = QEventLoop()
    worker.finished.connect(loop.quit)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    worker.wait(timeout_ms)
    QApplication.processEvents()


def test_worker_analyzes_only_missing_or_non_current_profiles(tmp_path: Path) -> None:
    ensure_app()
    current = _profile()
    stale = _profile(analysis_version=CURRENT_DANCEABILITY_VERSION + 1)
    analyzer = _FakeAnalyzer(current)
    repository = _FakeRepository()
    missing_path = tmp_path / "missing.flac"
    stale_path = tmp_path / "stale.flac"
    current_path = tmp_path / "current.flac"
    records = [
        TrackRecord(path=str(missing_path)),
        TrackRecord(path=str(stale_path), danceability_profile=stale),
        TrackRecord(path=str(current_path), danceability_profile=current),
    ]
    worker = DanceabilityCompletionWorker(danceability_analyzer=analyzer)

    worker.start(records, repository, max_workers=1)
    _wait_for_worker(worker)

    assert analyzer.calls == [missing_path, stale_path]


def test_worker_replays_repository_cache_without_reanalyzing(tmp_path: Path) -> None:
    ensure_app()
    path = tmp_path / "cached.flac"
    profile = _profile()
    analyzer = _FakeAnalyzer(profile)
    repository = _FakeRepository({str(path): profile})
    progress_events: list[tuple[str, DanceabilityProfile | None]] = []
    worker = DanceabilityCompletionWorker(danceability_analyzer=analyzer)
    worker.progress.connect(
        lambda emitted_path, emitted_profile: progress_events.append((emitted_path, emitted_profile))
    )

    worker.start([TrackRecord(path=str(path))], repository, max_workers=1)
    _wait_for_worker(worker)

    assert analyzer.calls == []
    assert progress_events == [(str(path), profile)]
    assert repository.updated == {}


def test_worker_persists_each_analyzed_profile(tmp_path: Path) -> None:
    ensure_app()
    path = tmp_path / "track.flac"
    profile = _profile()
    repository = _FakeRepository()
    worker = DanceabilityCompletionWorker(danceability_analyzer=_FakeAnalyzer(profile))

    worker.start([TrackRecord(path=str(path))], repository, max_workers=1)
    _wait_for_worker(worker)

    assert repository.updated == {str(path): profile}


def test_worker_respects_cooperative_cancellation(tmp_path: Path) -> None:
    ensure_app()
    path = tmp_path / "track.flac"
    analyzer = _FakeAnalyzer(_profile())
    token = ScanCancellationToken()
    token.cancel()
    progress_events: list[tuple[str, DanceabilityProfile | None]] = []
    worker = DanceabilityCompletionWorker(danceability_analyzer=analyzer)
    worker.progress.connect(lambda emitted_path, profile: progress_events.append((emitted_path, profile)))

    worker.start([TrackRecord(path=str(path))], _FakeRepository(), token, max_workers=1)
    _wait_for_worker(worker)

    assert analyzer.calls == []
    assert progress_events == []


def test_worker_dispose_when_idle_is_safe_before_start_and_twice() -> None:
    ensure_app()
    worker = DanceabilityCompletionWorker()

    worker.dispose_when_idle()
    worker.dispose_when_idle()


def test_worker_shutdown_releases_runner_and_is_idempotent(tmp_path: Path) -> None:
    ensure_app()
    worker = DanceabilityCompletionWorker(danceability_analyzer=_FakeAnalyzer(_profile()))
    worker.start([TrackRecord(path=str(tmp_path / "track.flac"))], _FakeRepository(), max_workers=1)

    worker.shutdown()
    worker.shutdown()

    assert worker._runner is None
    assert not worker.is_running()
