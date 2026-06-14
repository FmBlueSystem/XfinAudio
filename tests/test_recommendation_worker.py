"""Tests for RecommendationWorker — background thread recommendation."""

from PySide6.QtCore import QObject, QThreadPool, Signal
from PySide6.QtWidgets import QApplication

from xfinaudio.desktop.recommendation_worker import RecommendationWorker
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation


class _ResultCollector(QObject):
    finished = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.results: list[PlaylistRecommendation] = []
        self.finished.connect(self._on_finished)

    def _on_finished(self, result: PlaylistRecommendation) -> None:
        self.results.append(result)


def test_worker_runs_recommendation_in_background(qapp: QApplication) -> None:
    records = [
        TrackRecord(
            path="/a.flac",
            title="A",
            artist="Artist A",
            bpm=128.0,
            camelot_key="11B",
            energy_level=7,
            metadata_status="complete",
        ),
        TrackRecord(
            path="/b.flac",
            title="B",
            artist="Artist B",
            bpm=129.0,
            camelot_key="12B",
            energy_level=7,
            metadata_status="complete",
        ),
    ]
    collector = _ResultCollector()
    token = {"cancelled": False}
    worker = RecommendationWorker(
        records=records,
        strategy="build",
        controls=None,
        token=token,
        callback=collector.finished.emit,
    )

    QThreadPool.globalInstance().start(worker)
    # Wait for worker to finish
    import time

    for _ in range(200):
        qapp.processEvents()
        if collector.results:
            break
        time.sleep(0.01)

    assert len(collector.results) == 1
    assert collector.results[0].ordered_tracks[0].path == "/a.flac"


def test_worker_respects_cancellation_token(qapp: QApplication) -> None:
    records = [
        TrackRecord(
            path="/a.flac",
            title="A",
            bpm=128.0,
            camelot_key="11B",
            energy_level=7,
            metadata_status="complete",
        ),
    ]
    collector = _ResultCollector()
    token = {"cancelled": True}
    worker = RecommendationWorker(
        records=records,
        strategy="build",
        controls=None,
        token=token,
        callback=collector.finished.emit,
    )

    QThreadPool.globalInstance().start(worker)
    import time

    time.sleep(0.05)

    assert collector.results == []
