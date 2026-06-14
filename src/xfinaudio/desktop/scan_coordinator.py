"""Qt-aware scan orchestration extracted from ``MainWindow``.

``ScanCoordinator`` owns the scan state-machine and signal-handler logic that
previously lived on ``MainWindow``. It reads state and widgets through a
structural ``ScanHost`` handle (the ``MainWindow``), following the
``ExportCoordinator``/``ExportHost`` precedent. The ``ScanController`` thread
lifetime and signal wiring stay in ``MainWindow``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from PySide6.QtCore import QCoreApplication, Slot

from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import ScanCancellationToken, ScanProgress

_RECOMMENDATION_READY_GUIDANCE = QCoreApplication.translate(
    "MainWindow",
    "Selected row starts the playlist; multiple selected rows set the opening order. "
    "Up to 25 candidates are used for interactive speed. Choose a strategy, then click Recommend Playlist.",
)


class ScanHost(Protocol):
    """Structural host boundary for ``ScanCoordinator``.

    Declares only the ``MainWindow`` members the coordinator reads or calls,
    decoupling scan orchestration from the concrete window type.
    """

    selected_folder: Path | None
    scanned_records: list[TrackRecord]
    current_scan_cancellation_token: ScanCancellationToken | None
    _pre_scan_records_by_path: dict[str, TrackRecord]
    _state: Any
    _scan_controller: Any
    _library_screen: Any
    _build_screen: Any
    scan_progress_label: Any
    status_label: Any
    library_guidance_label: Any
    recommendation_guidance_label: Any

    def tr(self, text: str) -> str: ...
    def _sync_state(self) -> None: ...
    def show_tracks(
        self,
        records: list[TrackRecord],
        complete_count: int | None = None,
        incomplete_count: int | None = None,
    ) -> None: ...
    def _clear_scan_dependent_state(self) -> None: ...
    def _refresh_idle_action_state(self) -> None: ...
    def _cancel_spectral_completion_worker(self) -> None: ...


class ScanCoordinator:
    """Qt-aware scan orchestration extracted from MainWindow.

    State and widget access flow through ``host`` (the ``MainWindow``); the
    ``ScanController`` thread/worker lifetime remains owned by ``MainWindow``.
    """

    def __init__(self, host: ScanHost) -> None:
        self._host = host

    def scan_selected_folder(self) -> None:
        """Scan the selected folder, persist records, and refresh table/status widgets."""
        host = self._host
        if host.selected_folder is None:
            host.status_label.setText(host.tr("Choose a folder before scanning"))
            host.library_guidance_label.setText(
                host.tr("Choose a Mixed In Key processed folder before scanning metadata.")
            )
            return
        host._cancel_spectral_completion_worker()
        host._pre_scan_records_by_path = {record.path: record for record in host.scanned_records}
        self.begin_scan_state()
        token = host.current_scan_cancellation_token
        folder = host.selected_folder
        if token is None or folder is None:  # pragma: no cover - guarded by begin_scan_state and folder check
            raise RuntimeError("Scan state was not initialized before starting the scan worker")
        self._start_scan_worker(folder, token)

    def begin_scan_state(self) -> None:
        """Prepare synchronous scan state and enable cooperative cancellation."""
        host = self._host
        host.current_scan_cancellation_token = ScanCancellationToken()
        host._library_screen.scan_button.setEnabled(False)
        host._build_screen.recommend_button.setEnabled(False)
        host._library_screen.cancel_button.setEnabled(True)
        host.scan_progress_label.setText(host.tr("Scan progress: starting"))
        host.status_label.setText(host.tr("Scanning metadata"))
        host._sync_state()

    def _end_scan_state(self) -> None:
        """Clear scan state after scan completion or cancellation."""
        host = self._host
        host.current_scan_cancellation_token = None
        host._state.scan_progress_count = 0
        host._refresh_idle_action_state()
        host._sync_state()

    def _start_scan_worker(self, folder: Path, token: ScanCancellationToken) -> None:
        """Delegate thread/worker construction to the scan controller."""
        self._host._scan_controller.start_scan(folder, token)

    @Slot(object)
    def on_completed(self, result: Any) -> None:
        """Render a completed background scan result."""
        host = self._host
        if result.cancelled:
            host._clear_scan_dependent_state()
            self._end_scan_state()
            host.status_label.setText(host.tr("Scan canceled; no partial results were saved"))
            host.recommendation_guidance_label.setText(host.tr("Scan metadata before recommending a playlist."))
            return
        host.scanned_records = result.records
        host._sync_state()
        host.show_tracks(result.records, result.complete_count, result.incomplete_count)
        self._end_scan_state()
        self._show_scan_completion_status(result.records)
        host.recommendation_guidance_label.setText(
            _RECOMMENDATION_READY_GUIDANCE
            if host.scanned_records
            else host.tr("No tracks found. Choose another folder or re-scan after adding supported audio files.")
        )

    def _show_scan_completion_status(self, records: list[TrackRecord]) -> None:
        """Show either first-scan counts or refresh delta compared with the previous visible library."""
        host = self._host
        if not host._pre_scan_records_by_path:
            return
        before_records = list(host._pre_scan_records_by_path.values())
        before_incomplete = sum(1 for record in before_records if record.metadata_status == "incomplete")
        after_incomplete = sum(1 for record in records if record.metadata_status == "incomplete")
        fixed_count = sum(
            1
            for record in records
            if record.metadata_status == "complete"
            and host._pre_scan_records_by_path.get(record.path) is not None
            and host._pre_scan_records_by_path[record.path].metadata_status == "incomplete"
        )
        host.status_label.setText(
            host.tr("Refresh complete: {0} incomplete → {1} incomplete; {2} fixed").format(
                before_incomplete, after_incomplete, fixed_count
            )
        )
        host._pre_scan_records_by_path = {}

    @Slot(object)
    def on_failed(self, error: object) -> None:
        """Recover the UI if a background scan fails."""
        host = self._host
        self._end_scan_state()
        host.status_label.setText(host.tr("Scan failed: {0}").format(error))

    def on_progress(self, progress: ScanProgress) -> None:
        """Render scan progress from the workflow service."""
        host = self._host
        host.scan_progress_label.setText(
            host.tr("Scan progress: {0}/{1} - {2}").format(
                progress.processed_count, progress.total_count, progress.current_path
            )
        )
        host._state.scan_progress_count = progress.processed_count
        host._sync_state()

    def cancel(self) -> None:
        """Request cancellation for the current scan."""
        host = self._host
        if host.current_scan_cancellation_token is not None:
            host.current_scan_cancellation_token.cancel()
        host._scan_controller.cancel()
        host._library_screen.cancel_button.setEnabled(False)
        host.status_label.setText(host.tr("Cancel requested; waiting for current file to finish"))
