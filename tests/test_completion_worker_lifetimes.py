"""Regression tests for completion-worker Python/Qt lifetimes."""

from __future__ import annotations

import contextlib
import gc
import threading
import time
import weakref
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

from xfinaudio.audio.danceability import DanceabilityProfile
from xfinaudio.audio.spectral_profile import EdgeSpectralProfile, SpectralProfile
from xfinaudio.desktop.danceability_completion_worker import DanceabilityCompletionWorker
from xfinaudio.desktop.edge_spectral_completion_worker import EdgeSpectralCompletionWorker
from xfinaudio.desktop.spectral_completion_worker import SpectralCompletionWorker
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import ScanCancellationToken

_EXISTING_APP = QApplication.instance()
_APP: QApplication = _EXISTING_APP if isinstance(_EXISTING_APP, QApplication) else QApplication([])


def _spectral_profile() -> SpectralProfile:
    return SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")


def _danceability_profile() -> DanceabilityProfile:
    return DanceabilityProfile(score=0.72, pulse_clarity=0.8, tempo_confidence=0.9, percussive_ratio=0.6)


def _edge_spectral_profile() -> EdgeSpectralProfile:
    return EdgeSpectralProfile(
        intro=_spectral_profile(),
        outro=SpectralProfile(red_ratio=0.05, green_ratio=0.05, blue_ratio=0.9, dominant_color="BLUE"),
    )


WORKER_CASES = [
    pytest.param(SpectralCompletionWorker, "spectral_analyzer", _spectral_profile, id="spectral"),
    pytest.param(DanceabilityCompletionWorker, "danceability_analyzer", _danceability_profile, id="danceability"),
    pytest.param(
        EdgeSpectralCompletionWorker,
        "edge_spectral_analyzer",
        _edge_spectral_profile,
        id="edge-spectral",
    ),
]


class _BlockingAnalyzer:
    def __init__(self, profile: Any) -> None:
        self.profile = profile
        self.started = threading.Event()
        self.release = threading.Event()
        self.completed = threading.Event()

    def analyze(self, _path: Path) -> Any:
        self.started.set()
        if not self.release.wait(5):
            raise TimeoutError("Test did not release the fake analyzer")
        self.completed.set()
        return self.profile


class _FakeRepository:
    def __init__(self) -> None:
        self.updated = threading.Event()

    def load_spectral_profile_cache(self, _paths: list[str]) -> dict[str, Any]:
        return {}

    def load_danceability_profile_cache(self, _paths: list[str]) -> dict[str, Any]:
        return {}

    def load_edge_spectral_profile_cache(self, _paths: list[str]) -> dict[str, Any]:
        return {}

    def update_spectral_profile(self, _path: str, _profile: SpectralProfile) -> bool:
        self.updated.set()
        return True

    def update_danceability_profile(self, _path: str, _profile: DanceabilityProfile) -> bool:
        self.updated.set()
        return True

    def update_edge_spectral_profile(self, _path: str, _profile: EdgeSpectralProfile) -> bool:
        self.updated.set()
        return True


def _pump_events_until(predicate: Any, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        QApplication.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        gc.collect()
        if predicate():
            return True
        time.sleep(0.001)
    return bool(predicate())


def _make_worker(worker_class: type[Any], analyzer_argument: str, analyzer: _BlockingAnalyzer) -> Any:
    return worker_class(**{analyzer_argument: analyzer})


def _in_flight_registries() -> list[set[Any]]:
    from xfinaudio.desktop import (
        danceability_completion_worker,
        edge_spectral_completion_worker,
        spectral_completion_worker,
    )

    return [
        spectral_completion_worker._IN_FLIGHT_WORKERS,
        danceability_completion_worker._IN_FLIGHT_WORKERS,
        edge_spectral_completion_worker._IN_FLIGHT_WORKERS,
    ]


@pytest.fixture(autouse=True)
def _no_worker_outlives_its_test() -> Any:
    """Stop every worker this test started before the next module runs.

    A thread that survives its own test is not this test's problem — it is the
    next one's, and it shows up as a segfault in an unrelated module. Draining
    the in-flight registries here keeps a lifetime failure attributable to the
    test that caused it.
    """
    yield
    for registry in _in_flight_registries():
        for worker in list(registry):
            with contextlib.suppress(RuntimeError):
                worker.shutdown()
        registry.clear()
    _pump_events_until(lambda: True, timeout=0.05)


@pytest.mark.parametrize(("worker_class", "analyzer_argument", "profile_factory"), WORKER_CASES)
def test_running_worker_survives_when_caller_drops_last_reference(
    tmp_path: Path,
    worker_class: type[Any],
    analyzer_argument: str,
    profile_factory: Any,
) -> None:
    analyzer = _BlockingAnalyzer(profile_factory())
    repository = _FakeRepository()
    finished = threading.Event()
    worker = _make_worker(worker_class, analyzer_argument, analyzer)
    worker.finished.connect(finished.set)
    worker.start([TrackRecord(path=str(tmp_path / "track.flac"))], repository, max_workers=1)
    assert analyzer.started.wait(2)

    worker_reference = weakref.ref(worker)
    worker = None
    gc.collect()
    retained_while_running = worker_reference() is not None

    analyzer.release.set()
    assert _pump_events_until(finished.is_set)
    assert analyzer.completed.is_set()
    assert repository.updated.is_set()
    assert retained_while_running


@pytest.mark.parametrize(("worker_class", "analyzer_argument", "profile_factory"), WORKER_CASES)
def test_rapid_cancel_and_restart_churn_leaves_no_run_dangling(
    tmp_path: Path,
    worker_class: type[Any],
    analyzer_argument: str,
    profile_factory: Any,
) -> None:
    for index in range(5):
        analyzer = _BlockingAnalyzer(profile_factory())
        token = ScanCancellationToken()
        worker = _make_worker(worker_class, analyzer_argument, analyzer)
        worker.start(
            [TrackRecord(path=str(tmp_path / f"track-{index}.flac"))],
            _FakeRepository(),
            token,
            max_workers=1,
        )
        assert analyzer.started.wait(2)

        worker.cancel(timeout_ms=0)
        worker_reference = weakref.ref(worker)
        worker = None
        gc.collect()
        retained_while_running = worker_reference() is not None

        analyzer.release.set()
        assert _pump_events_until(analyzer.completed.is_set)
        assert _pump_events_until(lambda reference=worker_reference: reference() is None)
        assert retained_while_running


@pytest.mark.parametrize(("worker_class", "analyzer_argument", "profile_factory"), WORKER_CASES)
def test_dispose_when_idle_releases_only_after_thread_finishes(
    tmp_path: Path,
    worker_class: type[Any],
    analyzer_argument: str,
    profile_factory: Any,
) -> None:
    analyzer = _BlockingAnalyzer(profile_factory())
    worker = _make_worker(worker_class, analyzer_argument, analyzer)
    worker.start([TrackRecord(path=str(tmp_path / "track.flac"))], _FakeRepository(), max_workers=1)
    assert analyzer.started.wait(2)

    worker.dispose_when_idle()
    worker_reference = weakref.ref(worker)
    worker = None
    gc.collect()
    assert worker_reference() is not None

    analyzer.release.set()
    assert _pump_events_until(analyzer.completed.is_set)
    assert _pump_events_until(lambda: worker_reference() is None)


@pytest.mark.parametrize(("worker_class", "analyzer_argument", "profile_factory"), WORKER_CASES)
def test_shutdown_stops_running_worker_and_is_idempotent(
    tmp_path: Path,
    worker_class: type[Any],
    analyzer_argument: str,
    profile_factory: Any,
) -> None:
    analyzer = _BlockingAnalyzer(profile_factory())
    token = ScanCancellationToken()
    worker = _make_worker(worker_class, analyzer_argument, analyzer)
    worker.start(
        [TrackRecord(path=str(tmp_path / "track.flac"))],
        _FakeRepository(),
        token,
        max_workers=1,
    )
    assert analyzer.started.wait(2)
    release_timer = threading.Timer(0.02, analyzer.release.set)
    release_timer.start()

    worker.shutdown(timeout_ms=500)
    worker.shutdown(timeout_ms=500)

    release_timer.join()
    assert analyzer.completed.is_set()
    assert not worker.is_running()


@pytest.mark.parametrize(("worker_class", "analyzer_argument", "profile_factory"), WORKER_CASES)
def test_deleting_a_worker_mid_run_does_not_abort_on_a_live_thread(
    tmp_path: Path,
    worker_class: type[Any],
    analyzer_argument: str,
    profile_factory: Any,
) -> None:
    """Regression: a parented QThread is destroyed with its owner.

    `~QObject` calls `deleteChildren()`, and `~QThread` calls qFatal — which
    aborts the process, not merely warns — when the thread is still running.
    A crash report showed exactly that stack on the main thread while another
    QThread sat in `QThread::exec()`.
    """
    analyzer = _BlockingAnalyzer(profile_factory())
    worker = _make_worker(worker_class, analyzer_argument, analyzer)
    worker.start([TrackRecord(path=str(tmp_path / "track.flac"))], _FakeRepository(), max_workers=1)
    assert analyzer.started.wait(2)
    thread = worker._thread
    assert thread is not None and thread.isRunning()

    # The thread must not be a Qt child: that parentage is what turns an
    # ordinary deleteLater into an abort.
    assert not [child for child in worker.children() if child is thread]

    worker.deleteLater()
    threading.Timer(0.02, analyzer.release.set).start()

    assert _pump_events_until(lambda: not thread.isRunning())
