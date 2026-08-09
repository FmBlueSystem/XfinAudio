"""Focused tests for sequential background-analysis orchestration."""

from __future__ import annotations

from unittest.mock import Mock

from PySide6.QtWidgets import QApplication

from xfinaudio.audio.danceability import DanceabilityProfile
from xfinaudio.audio.spectral_profile import CURRENT_ANALYSIS_VERSION, EdgeSpectralProfile, SpectralProfile
from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.library.models import TrackRecord


class _FakeScanService:
    def scan(self, *args: object, **kwargs: object) -> list[TrackRecord]:
        return []


class _FakeRepository:
    def save_scan_results(self, records: list[TrackRecord]) -> None:
        pass


def _ensure_app() -> QApplication:
    existing = QApplication.instance()
    return existing if isinstance(existing, QApplication) else QApplication([])


def _worker_mock() -> Mock:
    worker = Mock()
    worker.progress = Mock()
    worker.progress_updated = Mock()
    worker.finished = Mock()
    worker.failed = Mock()
    return worker


def _spectral_profile() -> SpectralProfile:
    return SpectralProfile(
        red_ratio=0.9,
        green_ratio=0.05,
        blue_ratio=0.05,
        dominant_color="RED",
        analysis_version=CURRENT_ANALYSIS_VERSION,
    )


def _danceability_profile() -> DanceabilityProfile:
    return DanceabilityProfile(
        score=0.72,
        pulse_clarity=0.8,
        tempo_confidence=0.9,
        percussive_ratio=0.6,
    )


def test_spectral_completion_starts_danceability_worker_after_finish(monkeypatch) -> None:
    _ensure_app()
    spectral_worker = _worker_mock()
    danceability_worker = _worker_mock()
    monkeypatch.setattr(
        "xfinaudio.desktop.library_controller.SpectralCompletionWorker",
        Mock(return_value=spectral_worker),
    )
    danceability_factory = Mock(return_value=danceability_worker)
    monkeypatch.setattr(
        "xfinaudio.desktop.library_controller.DanceabilityCompletionWorker",
        danceability_factory,
    )
    window = MainWindow(scan_service=_FakeScanService(), repository=_FakeRepository())
    records = [TrackRecord(path="/music/track.flac")]

    window._library_controller.start_spectral_completion_worker(records)

    assert spectral_worker.start.call_count == 1
    assert danceability_factory.call_count == 0

    window._library_controller.on_spectral_completion_finished()

    danceability_worker.start.assert_called_once()
    assert danceability_worker.start.call_args.args[0] == records


def test_danceability_starts_directly_when_no_spectral_work_is_pending(monkeypatch) -> None:
    _ensure_app()
    spectral_factory = Mock()
    danceability_worker = _worker_mock()
    monkeypatch.setattr(
        "xfinaudio.desktop.library_controller.SpectralCompletionWorker",
        spectral_factory,
    )
    monkeypatch.setattr(
        "xfinaudio.desktop.library_controller.DanceabilityCompletionWorker",
        Mock(return_value=danceability_worker),
    )
    window = MainWindow(scan_service=_FakeScanService(), repository=_FakeRepository())
    records = [TrackRecord(path="/music/track.flac", spectral_profile=_spectral_profile())]

    window._library_controller.start_spectral_completion_worker(records)

    spectral_factory.assert_not_called()
    danceability_worker.start.assert_called_once()
    assert danceability_worker.start.call_args.args[0] == records


def test_danceability_profile_ready_updates_state_and_requests_sync(monkeypatch) -> None:
    _ensure_app()
    window = MainWindow(scan_service=_FakeScanService(), repository=_FakeRepository())
    controller = window._library_controller
    record = TrackRecord(path="/music/track.flac")
    controller._state = controller._state.model_copy(
        update={"scanned_records": [record], "records_by_path": {record.path: record}}
    )
    request_sync = Mock()
    monkeypatch.setattr(controller, "_request_sync", request_sync)
    profile = _danceability_profile()

    controller.on_danceability_profile_ready(record.path, profile)

    assert controller._state.scanned_records[0].danceability_profile == profile
    assert controller._state.records_by_path[record.path].danceability_profile == profile
    request_sync.assert_called_once_with()


def test_danceability_completion_starts_edge_worker_after_finish(monkeypatch) -> None:
    _ensure_app()
    danceability_worker = _worker_mock()
    edge_worker = _worker_mock()
    monkeypatch.setattr(
        "xfinaudio.desktop.library_controller.DanceabilityCompletionWorker",
        Mock(return_value=danceability_worker),
    )
    edge_factory = Mock(return_value=edge_worker)
    monkeypatch.setattr("xfinaudio.desktop.library_controller.EdgeSpectralCompletionWorker", edge_factory)
    window = MainWindow(scan_service=_FakeScanService(), repository=_FakeRepository())
    records = [TrackRecord(path="/music/track.flac", spectral_profile=_spectral_profile())]

    window._library_controller.start_danceability_completion_worker(records)

    assert edge_factory.call_count == 0
    window._library_controller.on_danceability_completion_finished()
    edge_worker.start.assert_called_once()
    assert edge_worker.start.call_args.args[0] == records


def test_edge_profile_ready_updates_state_and_requests_sync(monkeypatch) -> None:
    _ensure_app()
    window = MainWindow(scan_service=_FakeScanService(), repository=_FakeRepository())
    controller = window._library_controller
    record = TrackRecord(path="/music/track.flac")
    controller._state = controller._state.model_copy(
        update={"scanned_records": [record], "records_by_path": {record.path: record}}
    )
    request_sync = Mock()
    monkeypatch.setattr(controller, "_request_sync", request_sync)
    edge = _spectral_profile()
    profile = EdgeSpectralProfile(intro=edge, outro=edge)

    controller.on_edge_spectral_profile_ready(record.path, profile)

    assert controller._state.scanned_records[0].edge_spectral_profile == profile
    assert controller._state.records_by_path[record.path].edge_spectral_profile == profile
    request_sync.assert_called_once_with()


def test_shutdown_tears_down_all_completion_workers() -> None:
    _ensure_app()
    window = MainWindow(scan_service=_FakeScanService(), repository=_FakeRepository())
    spectral_worker = _worker_mock()
    danceability_worker = _worker_mock()
    edge_worker = _worker_mock()
    window._library_controller._spectral_completion_worker = spectral_worker
    window._library_controller._danceability_completion_worker = danceability_worker
    window._library_controller._edge_spectral_completion_worker = edge_worker

    window._library_controller.shutdown()

    spectral_worker.shutdown.assert_called_once_with()
    danceability_worker.shutdown.assert_called_once_with()
    edge_worker.shutdown.assert_called_once_with()
    assert window._library_controller._spectral_completion_worker is None
    assert window._library_controller._danceability_completion_worker is None
    assert window._library_controller._edge_spectral_completion_worker is None
