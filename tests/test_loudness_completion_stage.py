from __future__ import annotations

import threading
from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from xfinaudio.audio.loudness import LoudnessProfile, LoudnessStatus
from xfinaudio.audio.spectral_profile import CURRENT_EDGE_ANALYSIS_VERSION, EdgeSpectralProfile, SpectralProfile
from xfinaudio.config.settings import AppSettings, LoudnessSettings
from xfinaudio.desktop import library_controller, window_factory
from xfinaudio.desktop.background_completion_stage import BackgroundCompletionStage
from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.library.models import TrackRecord


def _profile() -> LoudnessProfile:
    return LoudnessProfile(
        lufs_integrated=-10.0,
        loudness_range_lra=4.0,
        true_peak_dbtp=-1.0,
        status=LoudnessStatus.MEASURED,
        engine_fingerprint="ffmpeg-test",
    )


def _edge_profile() -> EdgeSpectralProfile:
    spectral = SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")
    return EdgeSpectralProfile(intro=spectral, outro=spectral, analysis_version=CURRENT_EDGE_ANALYSIS_VERSION)


def test_background_stage_emits_result_and_invokes_cancel_at_shutdown() -> None:
    app = QApplication.instance() or QApplication([])
    stage = BackgroundCompletionStage()
    results: list[tuple[str, object]] = []
    cancelled: list[bool] = []
    loop = QEventLoop()
    stage.result.connect(lambda path, profile: results.append((path, profile)))
    stage.finished.connect(loop.quit)
    stage.start(lambda emit: emit("/track.flac", _profile()), cancel=lambda: cancelled.append(True))
    QTimer.singleShot(1000, loop.quit)
    loop.exec()
    stage.shutdown()

    assert results == [("/track.flac", _profile())]
    assert cancelled == [True]
    assert app is QApplication.instance()


def test_background_stage_terminal_shutdown_waits_without_a_timeout() -> None:
    stage = BackgroundCompletionStage()
    thread = Mock()
    thread.isRunning.return_value = True
    stage._thread = thread  # type: ignore[assignment]

    stage.shutdown()

    thread.wait.assert_called_once_with()


def test_window_close_terminates_its_loudness_stage_thread(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])

    class Repository:
        def save_scan_results(self, records, **kwargs):
            pass

    class ScanService:
        def scan(self, *_args, **_kwargs):
            return []

    class BlockingService:
        def __init__(self) -> None:
            self.started = threading.Event()
            self.cancelled = threading.Event()

        def complete(self, *_args, **_kwargs) -> None:
            self.started.set()
            self.cancelled.wait(1)

        def cancel(self) -> None:
            self.cancelled.set()

    monkeypatch.setattr(window_factory, "create_loudness_completion_service", lambda: None)
    window = MainWindow(scan_service=ScanService(), repository=Repository())
    service = BlockingService()
    controller = window._library_controller
    controller._loudness_completion_service = service
    controller.start_loudness_completion([TrackRecord(path="/track.flac")])
    stage = controller._loudness_completion_stage
    assert stage is not None
    assert service.started.wait(1)

    try:
        window.close()
        assert controller._loudness_completion_stage is None
        assert not stage.is_running()
    finally:
        controller.shutdown()
        stage.shutdown()
    assert app is QApplication.instance()


def test_window_close_reaps_a_loudness_stage_cancelled_before_shutdown(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])

    class Repository:
        def save_scan_results(self, records, **kwargs):
            pass

    class ScanService:
        def scan(self, *_args, **_kwargs):
            return []

    class DelayedCancellationService:
        def __init__(self) -> None:
            self.started = threading.Event()
            self.cancelled = threading.Event()
            self.release = threading.Event()

        def complete(self, *_args, **_kwargs) -> None:
            self.started.set()
            self.cancelled.wait(1)
            self.release.wait(1)

        def cancel(self) -> None:
            self.cancelled.set()

    monkeypatch.setattr(window_factory, "create_loudness_completion_service", lambda: None)
    window = MainWindow(scan_service=ScanService(), repository=Repository())
    service = DelayedCancellationService()
    controller = window._library_controller
    controller._loudness_completion_service = service
    controller.start_loudness_completion([TrackRecord(path="/track.flac")])
    stage = controller._loudness_completion_stage
    assert stage is not None
    assert service.started.wait(1)

    controller.cancel_loudness_completion()
    assert stage.is_running()
    assert stage in controller._loudness_completion_stages
    service.release.set()
    window.close()
    assert not stage.is_running()
    assert app is QApplication.instance()


def test_controller_starts_after_edge_without_missing_work_uses_priority_and_updates_immutably(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])

    class Repository:
        def save_scan_results(self, records, **kwargs):
            pass

    class Service:
        def __init__(self) -> None:
            self.calls: list[dict] = []
            self.cancelled = 0

        def complete(self, records, repository, **kwargs) -> None:
            self.calls.append(kwargs)
            if records:
                kwargs["on_result"](records[0].path, _profile())

        def cancel(self) -> None:
            self.cancelled += 1

    class Signal:
        def __init__(self) -> None:
            self.callback = None

        def connect(self, callback) -> None:
            self.callback = callback

        def emit(self, *args) -> None:
            assert self.callback is not None
            self.callback(*args)

    class Stage:
        instances: list[Stage] = []

        def __init__(self, *args, **kwargs) -> None:
            self.result, self.finished = Signal(), Signal()
            self.cancel_callback = None
            self.cancelled = self.shutdown_called = 0
            self.instances.append(self)

        def start(self, task, *, cancel=None) -> None:
            self.cancel_callback = cancel
            task(self.result.emit)

        def cancel(self) -> None:
            self.cancelled += 1
            if self.cancel_callback is not None:
                self.cancel_callback()

        def shutdown(self) -> None:
            self.shutdown_called += 1

        def deleteLater(self) -> None:
            pass

    monkeypatch.setattr(library_controller, "BackgroundCompletionStage", Stage)

    class ScanService:
        def scan(self, *_args, **_kwargs):
            return []

    window = MainWindow(scan_service=ScanService(), repository=Repository())
    records = [TrackRecord(path=f"/{name}.flac", edge_spectral_profile=_edge_profile()) for name in "abc"]
    window._library_controller.populate_track_table(records)
    window._replace_app_state(
        window._state.model_copy(
            update={
                "last_recommendation": SimpleNamespace(ordered_tracks=[records[1]]),
            }
        )
    )
    window._library_controller.on_library_selection_changed([records[0].path])
    window._library_screen.tracks_table.setRowHidden(2, True)
    service = Service()
    window._library_controller._loudness_completion_service = service
    previous = window._state

    window._library_controller.start_edge_spectral_completion_worker(records)
    stage = Stage.instances[0]

    assert service.calls[0] == {
        "selected_paths": [records[0].path],
        "candidate_paths": [records[1].path],
        "visible_paths": [records[0].path, records[1].path],
        "on_result": stage.result.emit,
    }
    assert window._state is not previous
    assert window._state.records_by_path[records[0].path].loudness_profile == _profile()
    assert window._state.is_completing_loudness is True
    assert (window._state.loudness_progress_count, window._state.loudness_total_count) == (1, 3)
    window._library_controller.on_loudness_completion_finished(Stage())
    assert window._library_controller._loudness_completion_stage is stage
    assert window._state.is_completing_loudness is True
    window._library_controller.cancel_loudness_completion()
    assert stage.cancelled == service.cancelled == 1
    assert window._state.is_completing_loudness is False
    assert (window._state.loudness_progress_count, window._state.loudness_total_count) == (0, 0)
    previous = window._state
    stage.result.emit(records[0].path, _profile())
    assert window._state is previous
    window._library_controller.shutdown()
    assert app is QApplication.instance()


def test_controller_does_not_schedule_new_loudness_work_when_disabled(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])

    class Repository:
        def save_scan_results(self, records, **kwargs):
            pass

    class ScanService:
        def scan(self, *_args, **_kwargs):
            return []

    class Service:
        def __init__(self) -> None:
            self.calls = 0

        def complete(self, *_args, **_kwargs) -> None:
            self.calls += 1

        def cancel(self) -> None:
            pass

    window = MainWindow(
        scan_service=ScanService(),
        repository=Repository(),
        settings=AppSettings(loudness=LoudnessSettings(enabled=False)),
    )
    service = Service()
    controller = window._library_controller
    controller._loudness_completion_service = service

    controller.start_loudness_completion([TrackRecord(path="/track.flac")])

    assert service.calls == 0
    assert controller._loudness_completion_stage is None
    controller.shutdown()
    assert app is QApplication.instance()
