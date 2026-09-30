"""Isolate fatal Qt teardown regressions from the test runner."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "kind",
    [
        "recommendation",
        "scan",
        "copilot",
        "narrator",
        "replacement",
        "spectral",
        "danceability",
        "edge",
        "loudness",
        "retired_analysis",
    ],
)
def test_close_drains_slow_work_without_freezing_or_losing_committed_records(tmp_path, kind):
    script = r"""
import sys, time
from pathlib import Path
from types import SimpleNamespace
from PySide6.QtCore import QThread, QTimer
from PySide6.QtWidgets import QApplication
from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import ScanCancellationToken
from xfinaudio.library.track_repository import TrackRepository

app = QApplication([])
repo = TrackRepository(Path(sys.argv[1]))
repo.save_scan_results([TrackRecord(path="/saved.flac")])
window = MainWindow(scan_service=SimpleNamespace(), repository=repo)
window.show()
kind = sys.argv[2]
started, completed, ticks = [], [], []
def slow(*args, **kwargs):
    started.append(True)
    time.sleep(1.2)
    completed.append(True)
    return None
if kind in ("recommendation", "replacement"):
    service = window._recommendation_service
    service.workflow_service = SimpleNamespace(recommend=slow)
    service.start_recommendation([], "harmonic_journey")
    if kind == "replacement":
        QTimer.singleShot(30, lambda: service.start_recommendation([], "harmonic_journey"))
elif kind == "scan":
    service = window._scan_service
    service.workflow_service = SimpleNamespace(scan_folder=slow)
    service.start_scan(Path(sys.argv[1]).parent, ScanCancellationToken())
elif kind == "loudness":
    from xfinaudio.desktop.background_completion_stage import BackgroundCompletionStage
    stage = BackgroundCompletionStage(window)
    window._library_controller._loudness_completion_stage = stage
    stage.start(slow)
elif kind in ("spectral", "danceability", "edge", "retired_analysis"):
    from xfinaudio.desktop.spectral_completion_worker import SpectralCompletionWorker
    from xfinaudio.desktop.danceability_completion_worker import DanceabilityCompletionWorker
    from xfinaudio.desktop.edge_spectral_completion_worker import EdgeSpectralCompletionWorker
    cls, argument, attribute = {
        "spectral": (SpectralCompletionWorker, "spectral_analyzer", "_spectral_completion_worker"),
        "danceability": (DanceabilityCompletionWorker, "danceability_analyzer", "_danceability_completion_worker"),
        "edge": (EdgeSpectralCompletionWorker, "edge_spectral_analyzer", "_edge_spectral_completion_worker"),
        "retired_analysis": (SpectralCompletionWorker, "spectral_analyzer", "_spectral_completion_worker"),
    }[kind]
    worker = cls(window, **{argument: SimpleNamespace(analyze=slow)})
    setattr(window._library_controller, attribute, worker)
    worker.start([TrackRecord(path="/synthetic.flac")], repo, max_workers=1)
    if kind == "retired_analysis":
        QTimer.singleShot(30, window._library_controller.cancel_spectral_completion_worker)
else:
    service = window._ai_copilot if kind == "copilot" else window._ai_narrator
    service._start_worker(slow, 0)
def close():
    assert started
    start = time.monotonic()
    window.close()
    assert time.monotonic() - start < 0.25, "close blocked the event loop"
    assert window.isVisible(), "closed before work finished"
    QTimer.singleShot(20, lambda: ticks.append(True))
    QTimer.singleShot(40, window.close)
QTimer.singleShot(100, close)
QTimer.singleShot(6000, lambda: sys.exit(8))
app.exec()
assert completed and len(completed) == len(started)
assert ticks, "event loop did not run during shutdown"
assert not any(t.isRunning() for t in window.findChildren(QThread))
assert repo.list_tracks()[0].path == "/saved.flac"
print("DRAINED", flush=True)
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path / "library.sqlite3"), kind],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONFAULTHANDLER": "1"},
        capture_output=True,
        text=True,
        timeout=12,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "DRAINED" in result.stdout
    assert "QThread: Destroyed" not in result.stderr
