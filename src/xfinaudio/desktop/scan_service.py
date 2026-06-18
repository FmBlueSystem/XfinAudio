"""Qt scan service that owns worker lifecycle and scan UI state."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QCoreApplication, QObject, QThread, Signal, Slot

from xfinaudio.application.playlist_workflow import PlaylistWorkflowService
from xfinaudio.desktop._workers import ScanWorker
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import ScanCancellationToken, ScanProgress


def _unwired(*_args: Any, **_kwargs: Any) -> Any:
    raise RuntimeError("ScanService dependencies were not wired")


def progress_percent(processed_count: int, total_count: int) -> int:
    """Return clamped integer progress percentage for completed units."""
    if total_count <= 0:
        return 0
    processed = max(0, min(processed_count, total_count))
    return round((processed / total_count) * 100)


def progress_status_text(processed_count: int, total_count: int, elapsed_seconds: float) -> str:
    """Return progress percentage plus estimated time remaining."""
    percent = progress_percent(processed_count, total_count)
    if processed_count <= 0 or total_count <= 0 or elapsed_seconds <= 0:
        return f"{percent}% · estimating remaining"
    remaining_units = max(total_count - processed_count, 0)
    remaining_seconds = round((elapsed_seconds / processed_count) * remaining_units)
    minutes, seconds = divmod(remaining_seconds, 60)
    return f"{percent}% · {minutes}:{seconds:02d} remaining"


_RECOMMENDATION_READY_GUIDANCE = QCoreApplication.translate(
    "MainWindow",
    "Selected row starts the playlist; multiple selected rows set the opening order. "
    "Up to 25 candidates are used for interactive speed. Choose a strategy, then click Recommend Playlist.",
)


class ScanService(QObject):
    """Manage scan worker lifecycle and scan state-machine."""

    scan_progress_updated = Signal(object)
    scan_completed = Signal(object)
    scan_failed = Signal(object)
    worker_cleared = Signal()

    def __init__(self, workflow_service: PlaylistWorkflowService, *, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.workflow_service = workflow_service
        self.current_scan_cancellation_token: ScanCancellationToken | None = None
        self._scan_thread: QThread | None = None
        self._scan_worker: ScanWorker | None = None
        self._current_token: ScanCancellationToken | None = None
        self._current_request_id: int = 0
        self._pre_scan_records_by_path: dict[str, TrackRecord] = {}
        self._selected_folder: Callable[[], Path | None] = _unwired
        self._scanned_records: Callable[[], list[TrackRecord]] = _unwired
        self._set_scanned_records: Callable[[list[TrackRecord]], None] = _unwired
        self._state: Any = None
        self._library_screen: Any = None
        self._build_screen: Any = None
        self._status_label: Any = None
        self._scan_progress_label: Any = None
        self._library_guidance_label: Any = None
        self._recommendation_guidance_label: Any = None
        self._tr: Callable[[str], str] = lambda text: text
        self._sync_state: Callable[[], None] = _unwired
        self._show_tracks: Callable[[list[TrackRecord], int | None, int | None], None] = _unwired
        self._clear_scan_dependent_state: Callable[[], None] = _unwired
        self._refresh_idle_action_state: Callable[[], None] = _unwired
        self._cancel_spectral_completion_worker: Callable[[], None] = _unwired
        self._show_status_bar: Callable[[], None] = _unwired

    def set_state_accessors(
        self,
        *,
        selected_folder: Callable[[], Path | None],
        scanned_records: Callable[[], list[TrackRecord]],
        set_scanned_records: Callable[[list[TrackRecord]], None],
        state: Any,
    ) -> None:
        self._selected_folder = selected_folder
        self._scanned_records = scanned_records
        self._set_scanned_records = set_scanned_records
        self._state = state

    def set_ui(
        self,
        *,
        library_screen: Any,
        build_screen: Any,
        status_label: Any,
        scan_progress_label: Any,
        library_guidance_label: Any,
        recommendation_guidance_label: Any,
        tr: Callable[[str], str],
    ) -> None:
        self._library_screen = library_screen
        self._build_screen = build_screen
        self._status_label = status_label
        self._scan_progress_label = scan_progress_label
        self._library_guidance_label = library_guidance_label
        self._recommendation_guidance_label = recommendation_guidance_label
        self._tr = tr

    def set_actions(
        self,
        *,
        sync_state: Callable[[], None],
        show_tracks: Callable[[list[TrackRecord], int | None, int | None], None],
        clear_scan_dependent_state: Callable[[], None],
        refresh_idle_action_state: Callable[[], None],
        cancel_spectral_completion_worker: Callable[[], None],
        show_status_bar: Callable[[], None],
    ) -> None:
        self._sync_state = sync_state
        self._show_tracks = show_tracks
        self._clear_scan_dependent_state = clear_scan_dependent_state
        self._refresh_idle_action_state = refresh_idle_action_state
        self._cancel_spectral_completion_worker = cancel_spectral_completion_worker
        self._show_status_bar = show_status_bar

    def start_scan(self, folder: Path, token: ScanCancellationToken) -> None:
        """Start a background metadata scan for *folder* using the given *token*."""
        if self._scan_thread is not None and self._scan_thread.isRunning():
            self.cancel()
            self._scan_thread.wait(500)
        self._current_token = token
        self._current_request_id += 1
        rid = self._current_request_id
        self._start_scan_worker(folder, token, rid)

    def cancel(self) -> None:
        """Request cancellation for the current scan."""
        if self.current_scan_cancellation_token is not None:
            self.current_scan_cancellation_token.cancel()
        if self._current_token is not None:
            self._current_token.cancel()
        if self._scan_thread is not None and self._scan_thread.isRunning():
            self._scan_thread.requestInterruption()
            self._scan_thread.wait(500)
        if self._library_screen is not None:
            self._library_screen.cancel_button.setEnabled(False)
        if self._status_label is not None:
            self._status_label.setText(self._tr("Cancel requested; waiting for current file to finish"))

    def scan_selected_folder(self) -> None:
        """Scan the selected folder, persist records, and refresh table/status widgets."""
        self._require_wired()
        folder = self._selected_folder()
        if folder is None:
            self._status_label.setText(self._tr("Choose a folder before scanning"))
            self._library_guidance_label.setText(
                self._tr("Choose a Mixed In Key processed folder before scanning metadata.")
            )
            return
        self._cancel_spectral_completion_worker()
        self._pre_scan_records_by_path = {record.path: record for record in self._scanned_records()}
        self.begin_scan_state()
        token = self.current_scan_cancellation_token
        if token is None:  # pragma: no cover - guarded by begin_scan_state
            raise RuntimeError("Scan state was not initialized before starting the scan worker")
        self.start_scan(folder, token)

    def begin_scan_state(self) -> None:
        """Prepare synchronous scan state and enable cooperative cancellation."""
        self._require_wired()
        self.current_scan_cancellation_token = ScanCancellationToken()
        self._library_screen.scan_button.setEnabled(False)
        self._build_screen.recommend_button.setEnabled(False)
        self._library_screen.cancel_button.setEnabled(True)
        self._scan_progress_label.setText(self._tr("Scan progress: starting"))
        self._status_label.setText(self._tr("Scanning metadata"))
        self._show_status_bar()
        self._sync_state()

    def _end_scan_state(self) -> None:
        self.current_scan_cancellation_token = None
        self._state.scan_progress_count = 0
        self._refresh_idle_action_state()
        self._sync_state()

    @Slot(object)
    def on_completed(self, result: Any) -> None:
        """Render a completed background scan result."""
        self._require_wired()
        if result.cancelled:
            self._clear_scan_dependent_state()
            self._end_scan_state()
            self._status_label.setText(self._tr("Scan canceled; no partial results were saved"))
            self._recommendation_guidance_label.setText(self._tr("Scan metadata before recommending a playlist."))
            return
        self._set_scanned_records(result.records)
        self._sync_state()
        self._show_tracks(result.records, result.complete_count, result.incomplete_count)
        self._end_scan_state()
        self._show_scan_completion_status(result.records)
        self._recommendation_guidance_label.setText(
            _RECOMMENDATION_READY_GUIDANCE
            if self._scanned_records()
            else self._tr("No tracks found. Choose another folder or re-scan after adding supported audio files.")
        )

    @Slot(object)
    def on_failed(self, error: object) -> None:
        """Recover the UI if a background scan fails."""
        self._require_wired()
        self._end_scan_state()
        self._status_label.setText(self._tr("Scan failed: {0}").format(error))

    def on_progress(self, progress: ScanProgress) -> None:
        """Render scan progress from the workflow service."""
        self._require_wired()
        self._scan_progress_label.setText(
            self._tr("Scan progress: {0}/{1} - {2}").format(
                progress.processed_count, progress.total_count, progress.current_path
            )
        )
        self._state.scan_progress_count = progress.processed_count
        self._sync_state()

    def _start_scan_worker(self, folder: Path, token: ScanCancellationToken, request_id: int) -> None:
        thread = QThread(self)
        worker = ScanWorker(
            lambda progress_callback: self.workflow_service.scan_folder(
                folder,
                on_progress=progress_callback,
                cancellation_token=token,
                resolve_spectral_profiles=False,
            ),
            request_id=request_id,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_worker_progress)
        worker.finished.connect(lambda result, rid=request_id: self._on_worker_finished(result, rid))
        worker.failed.connect(lambda error, rid=request_id: self._on_worker_failed(error, rid))
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_worker_cleared)
        self._scan_thread = thread
        self._scan_worker = worker
        thread.start()

    @Slot(object)
    def _on_worker_progress(self, progress: object) -> None:
        self.scan_progress_updated.emit(progress)

    def _on_worker_finished(self, result: object, request_id: int | None = None) -> None:
        if request_id is not None and request_id != self._current_request_id:
            return
        self.scan_completed.emit(result)

    def _on_worker_failed(self, error: object, request_id: int | None = None) -> None:
        if request_id is not None and request_id != self._current_request_id:
            return
        self.scan_failed.emit(error)

    def _on_worker_cleared(self) -> None:
        sender_thread = self.sender()
        if sender_thread is not None and sender_thread is not self._scan_thread:
            return
        self._scan_thread = None
        self._scan_worker = None
        self.worker_cleared.emit()

    def _show_scan_completion_status(self, records: list[TrackRecord]) -> None:
        if not self._pre_scan_records_by_path:
            return
        before_records = list(self._pre_scan_records_by_path.values())
        before_incomplete = sum(1 for record in before_records if record.metadata_status == "incomplete")
        after_incomplete = sum(1 for record in records if record.metadata_status == "incomplete")
        fixed_count = sum(
            1
            for record in records
            if record.metadata_status == "complete"
            and self._pre_scan_records_by_path.get(record.path) is not None
            and self._pre_scan_records_by_path[record.path].metadata_status == "incomplete"
        )
        self._status_label.setText(
            self._tr("Refresh complete: {0} incomplete → {1} incomplete; {2} fixed").format(
                before_incomplete, after_incomplete, fixed_count
            )
        )
        self._pre_scan_records_by_path = {}

    def _require_wired(self) -> None:
        if any(
            value is None
            for value in (
                self._state,
                self._library_screen,
                self._build_screen,
                self._status_label,
                self._scan_progress_label,
                self._library_guidance_label,
                self._recommendation_guidance_label,
            )
        ):
            raise RuntimeError("ScanService dependencies were not wired")


__all__ = ["ScanService", "progress_percent", "progress_status_text"]
