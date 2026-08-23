from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from xfinaudio.audio.loudness import LoudnessProfile, LoudnessStatus
from xfinaudio.audio.spectral_profile import CURRENT_EDGE_ANALYSIS_VERSION, EdgeSpectralProfile, SpectralProfile
from xfinaudio.desktop import library_controller
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
                "selected_library_paths": [records[0].path],
                "last_recommendation": SimpleNamespace(ordered_tracks=[records[1]]),
            }
        )
    )
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
    window._library_controller.on_loudness_completion_finished(Stage())
    assert window._library_controller._loudness_completion_stage is stage
    window._library_controller.start_spectral_completion_worker([])
    assert stage.cancelled == service.cancelled == 1
    window._library_controller.shutdown()
    assert app is QApplication.instance()
