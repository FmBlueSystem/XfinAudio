"""Tests for the lazy spectral completion worker."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from xfinaudio.audio.spectral_profile import SpectralProfile
from xfinaudio.desktop import spectral_completion_worker
from xfinaudio.desktop.spectral_completion_worker import (
    SpectralCompletionWorker,
    _default_max_workers_for_analysis,
    _SpectralCompletionRunner,
)
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import ScanCancellationToken
from xfinaudio.library.track_repository import TrackRepository

_EXISTING_APP = QApplication.instance()
_APP: QApplication = _EXISTING_APP if isinstance(_EXISTING_APP, QApplication) else QApplication([])


def ensure_app() -> None:
    _ = _APP


class _FakeRepository:
    def __init__(self, profiles: dict[str, SpectralProfile] | None = None) -> None:
        self.updated: dict[str, SpectralProfile] = {}
        self._cache = profiles or {}

    def load_spectral_profile_cache(self, paths: list[str]) -> dict[str, tuple[int, int, SpectralProfile]]:
        result: dict[str, tuple[int, int, SpectralProfile]] = {}
        for path in paths:
            profile = self._cache.get(path)
            if profile is not None:
                result[path] = (0, 0, profile)
        return result

    def update_spectral_profile(self, path: str, profile: SpectralProfile) -> bool:
        self.updated[path] = profile
        return True


def test_default_max_workers_for_analysis_reserves_one_cpu() -> None:
    ensure_app()

    assert _default_max_workers_for_analysis(cpu_count=8) == 7
    assert _default_max_workers_for_analysis(cpu_count=1) == 1


def _wait_for_worker(worker: SpectralCompletionWorker, timeout_ms: int = 5000) -> None:
    loop = QEventLoop()
    worker.finished.connect(loop.quit)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    worker.wait(timeout_ms)
    QApplication.processEvents()


def test_worker_emits_progress_for_missing_profiles(monkeypatch) -> None:
    ensure_app()
    expected_profile = SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")
    monkeypatch.setattr(
        "xfinaudio.desktop.spectral_completion_worker.analyze_spectral_profile",
        lambda path: expected_profile,
    )

    records = [TrackRecord(path="/music/track.flac", title="Track", metadata_status="complete")]
    repo = _FakeRepository()
    worker = SpectralCompletionWorker()
    progress_events: list[tuple[str, SpectralProfile | None]] = []
    worker.progress.connect(lambda path, profile: progress_events.append((path, profile)))

    worker.start(records, repo)
    _wait_for_worker(worker)

    assert len(progress_events) == 1
    assert progress_events[0][0] == "/music/track.flac"
    assert progress_events[0][1] == expected_profile
    assert repo.updated == {"/music/track.flac": expected_profile}


def test_worker_skips_cached_profiles(monkeypatch) -> None:
    ensure_app()
    cached_profile = SpectralProfile(red_ratio=0.1, green_ratio=0.8, blue_ratio=0.1, dominant_color="GREEN")
    repo = _FakeRepository(profiles={"/music/track.flac": cached_profile})
    monkeypatch.setattr(
        "xfinaudio.desktop.spectral_completion_worker.analyze_spectral_profile",
        lambda path: pytest.fail("Should not analyze cached profile"),
    )

    records = [TrackRecord(path="/music/track.flac", title="Track", metadata_status="complete")]
    worker = SpectralCompletionWorker()
    progress_events: list[tuple[str, SpectralProfile | None]] = []
    worker.progress.connect(lambda path, profile: progress_events.append((path, profile)))

    worker.start(records, repo)
    _wait_for_worker(worker)

    assert len(progress_events) == 1
    assert progress_events[0][1] == cached_profile
    assert repo.updated == {}


def test_worker_emits_progress_updated_counts_cached_and_analyzed(monkeypatch) -> None:
    ensure_app()
    cached_profile = SpectralProfile(red_ratio=0.1, green_ratio=0.8, blue_ratio=0.1, dominant_color="GREEN")
    analyzed_profile = SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")
    repo = _FakeRepository(profiles={"/music/cached.flac": cached_profile})
    monkeypatch.setattr(
        "xfinaudio.desktop.spectral_completion_worker.analyze_spectral_profile",
        lambda path: analyzed_profile,
    )

    records = [
        TrackRecord(path="/music/cached.flac", title="Cached", metadata_status="complete"),
        TrackRecord(path="/music/analyzed.flac", title="Analyzed", metadata_status="complete"),
        TrackRecord(
            path="/music/complete.flac",
            title="Complete",
            metadata_status="complete",
            spectral_profile=SpectralProfile(
                red_ratio=0.2,
                green_ratio=0.2,
                blue_ratio=0.6,
                dominant_color="BLUE",
            ),
        ),
    ]
    worker = SpectralCompletionWorker()
    progress_updates: list[tuple[int, int]] = []
    worker.progress_updated.connect(lambda processed, total: progress_updates.append((processed, total)))

    worker.start(records, repo, max_workers=1)
    _wait_for_worker(worker)

    assert progress_updates == [(1, 2), (2, 2)]


def test_worker_respects_cancellation(monkeypatch) -> None:
    ensure_app()
    monkeypatch.setattr(
        "xfinaudio.desktop.spectral_completion_worker.analyze_spectral_profile",
        lambda path: pytest.fail("Should not analyze when cancelled"),
    )

    records = [TrackRecord(path="/music/track.flac", title="Track", metadata_status="complete")]
    token = ScanCancellationToken()
    token.cancel()
    worker = SpectralCompletionWorker()
    progress_events: list[tuple[str, SpectralProfile | None]] = []
    worker.progress.connect(lambda path, profile: progress_events.append((path, profile)))

    worker.start(records, _FakeRepository(), cancellation_token=token)
    _wait_for_worker(worker)

    assert progress_events == []


def test_repository_update_spectral_profile_persists_profile(tmp_path: Path) -> None:
    audio_path = tmp_path / "track.flac"
    audio_path.write_text("audio")
    repository = TrackRepository(tmp_path / "library.db")
    record = TrackRecord(path=str(audio_path), title="Track", metadata_status="complete")
    repository.save_scan_results([record])

    profile = SpectralProfile(
        red_ratio=0.9,
        green_ratio=0.05,
        blue_ratio=0.05,
        dominant_color="RED",
    )
    updated = repository.update_spectral_profile(str(audio_path), profile)

    assert updated is True
    restored = repository.list_tracks()[0]
    assert restored.spectral_profile == profile


def test_scan_folder_leaves_profiles_none_when_resolve_is_false(monkeypatch) -> None:
    from xfinaudio.library.scan_service import scan_folder

    root = Path("/library")
    audio_path = root / "track.flac"

    def fake_analyze(path: Path) -> SpectralProfile:
        return SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")

    monkeypatch.setattr("xfinaudio.library.scan_service.analyze_spectral_profile", fake_analyze)

    records = scan_folder(
        root,
        list_paths=lambda folder: [audio_path],
        read_tags=lambda path: {"title": ["Track"]},
        resolve_spectral_profiles=False,
    )

    assert len(records) == 1
    assert records[0].spectral_profile is None


def test_runner_uses_cpu_reservation_default(monkeypatch) -> None:
    ensure_app()
    monkeypatch.setattr(spectral_completion_worker.os, "cpu_count", lambda: 8)

    runner = _SpectralCompletionRunner([], _FakeRepository())

    assert runner._max_workers == 7


def test_runner_respects_explicit_max_workers(monkeypatch) -> None:
    ensure_app()
    monkeypatch.setattr(spectral_completion_worker.os, "cpu_count", lambda: 8)

    runner = _SpectralCompletionRunner([], _FakeRepository(), max_workers=3)

    assert runner._max_workers == 3
