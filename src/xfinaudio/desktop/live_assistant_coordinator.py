"""Live Assistant orchestration extracted from MainWindow.

The ``LiveAssistantCoordinator`` owns signal wiring and load-next logic,
reading state through the ``LiveAssistantHost`` Protocol to stay decoupled
from the concrete ``MainWindow`` type.
"""

from __future__ import annotations

from typing import Any, Protocol

from xfinaudio.library.models import TrackRecord


class LiveAssistantHost(Protocol):
    """Structural host boundary for ``LiveAssistantCoordinator``.

    Declares only the ``MainWindow`` members the coordinator reads or calls,
    decoupling live-assistant orchestration from the concrete window type.
    """

    _live_assistant_screen: Any
    workflow_tabs: Any
    _records_by_path: dict[str, TrackRecord]
    scanned_records: list[TrackRecord]

    def _on_preview_play_requested(self, path: str) -> None: ...
    def _on_live_load_next(self, path: str) -> None: ...


class LiveAssistantCoordinator:
    """Qt-aware Live Assistant orchestration extracted from MainWindow.

    State and widget access flow through ``host`` (the ``MainWindow``).
    """

    def __init__(self, host: LiveAssistantHost) -> None:
        self._host = host

    def connect_signals(self) -> None:
        """Wire LiveAssistantScreen signals to coordinator handlers."""
        host = self._host
        host._live_assistant_screen.exit_requested.connect(lambda: host.workflow_tabs.setCurrentIndex(0))
        host._live_assistant_screen.preview_requested.connect(host._on_preview_play_requested)
        host._live_assistant_screen.load_next_requested.connect(host._on_live_load_next)

    def load_next(self, path: str) -> None:
        """Handle load-next from Live Assistant: update current track and recalculate suggestions."""
        host = self._host
        record = host._records_by_path.get(path)
        if record is None:
            return
        host._live_assistant_screen.set_current_track(record)
        # Build candidate pool from scanned records excluding current track
        candidates = [r for r in host.scanned_records if r.path != path and r.metadata_status == "complete"][:25]
        host._live_assistant_screen.set_candidates(candidates)
