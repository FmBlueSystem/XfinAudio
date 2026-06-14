"""Background worker for running playlist recommendations off the main thread."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QRunnable

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation, recommend_playlist


class RecommendationWorker(QRunnable):
    """Runs recommend_playlist in a background thread.

    Emits the result via a callback on the main thread using
    QMetaObject.invokeMethod if the callback is a bound signal.
    """

    def __init__(
        self,
        records: list[TrackRecord],
        strategy: str,
        controls: DJControls | None,
        token: dict[str, bool],
        callback: Callable[[PlaylistRecommendation], Any],
    ) -> None:
        super().__init__()
        self.records = records
        self.strategy = strategy
        self.controls = controls
        self.token = token
        self.callback = callback

    def run(self) -> None:
        if self.token.get("cancelled", False):
            return

        try:
            result = recommend_playlist(
                self.records,
                self.strategy,
                controls=self.controls,
            )
        except Exception:
            # Silently fail if recommendation errors; caller should handle missing result
            return

        if self.token.get("cancelled", False):
            return

        self.callback(result)
