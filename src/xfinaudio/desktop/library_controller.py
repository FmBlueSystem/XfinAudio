"""Library state and spectral worker controller."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QFileDialog, QLabel, QWidget

from xfinaudio.application.playlist_workflow import PlaylistWorkflowService
from xfinaudio.config.settings import AppSettings
from xfinaudio.desktop import layout as _layout
from xfinaudio.desktop.app_state import AppState, SettingsPersistence
from xfinaudio.desktop.audio_player import AudioPlayer
from xfinaudio.desktop.library_filter import metadata_missing_field_records, metadata_status_records
from xfinaudio.desktop.rendering import (
    _format_missing_metadata,
    _format_spectral_color,
    _format_track_tags,
    _table_item,
)
from xfinaudio.desktop.review_view_model import ReviewViewModel
from xfinaudio.desktop.screens import BuildScreen, ExportScreen, LibraryScreen, MetadataScreen, ReviewScreen
from xfinaudio.desktop.spectral_completion_worker import SpectralCompletionWorker
from xfinaudio.desktop.table_populators import populate_library_table
from xfinaudio.library.models import TrackRecord

_TRACK_COLOR_COLUMN = 6
_TRACK_PATH_COLUMN = 11
_MISSING_METADATA_FILTERS = {
    "Missing BPM": "bpm",
    "Missing Key": "camelot_key",
    "Missing Energy": "energy_level",
}
_RECOMMENDATION_READY_GUIDANCE = (
    "Selected row starts the playlist; multiple selected rows set the opening order. "
    "Up to 25 candidates are used for interactive speed. Choose a strategy, then click Recommend Playlist."
)


@dataclass(frozen=True)
class LibraryControllerWidgets:
    library_screen: LibraryScreen
    build_screen: BuildScreen
    review_screen: ReviewScreen
    export_screen: ExportScreen
    metadata_screen: MetadataScreen
    folder_label: QLabel
    library_guidance_label: QLabel
    recommendation_guidance_label: QLabel
    status_label: QLabel


@dataclass(frozen=True)
class LibraryControllerAccess:
    settings_getter: Callable[[], AppSettings]
    settings_setter: Callable[[AppSettings], None]
    settings_repository: SettingsPersistence | None
    selected_paths: list[str]
    pre_scan_records_by_path: dict[str, TrackRecord]
    set_applied_copilot_variant: Callable[[str | None], None]
    set_recommendation_sections_expanded: Callable[[bool], None]
    clear_recommendation_review: Callable[[], None]
    selected_track_controls: Callable[[], object | None]
    apply_song_filter: Callable[..., None]
    state_setter: Callable[[AppState], None]
    export_metadata_status_to_serato: Callable[..., None]
    undo_manager: Any
    refresh_undo_state: Callable[[], None]
    workflow_tab_setter: Callable[[int], None]
    open_track: Callable[[str], object]
    live_load_next: Callable[[str], None]


class LibraryController:
    def __init__(
        self,
        *,
        state: AppState,
        workflow_service: PlaylistWorkflowService,
        widgets: LibraryControllerWidgets,
        access: LibraryControllerAccess,
        audio_player: AudioPlayer,
        sync_state: Callable[[], None],
        tr: Callable[[str], str],
        log: logging.Logger,
        parent: QWidget,
    ) -> None:
        self._state = state
        self._workflow_service = workflow_service
        self._widgets = widgets
        self._access = access
        self._audio_player = audio_player
        self._sync_state = sync_state
        self._tr = tr
        self._log = log
        self._parent = parent
        self._spectral_completion_worker: SpectralCompletionWorker | None = None
        self._active_song_search_query = ""
        # Ensure the spectral worker is shut down before this controller is
        # destroyed. Otherwise the QThread inside the worker outlives the
        # MainWindow and Qt prints "QThread: Destroyed while thread '' is
        # still running" at interpreter exit.
        self._parent.destroyed.connect(self.shutdown)

    @property
    def spectral_completion_worker(self) -> SpectralCompletionWorker | None:
        return self._spectral_completion_worker

    def choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self._parent, self._tr("Choose music folder"))
        if folder:
            self.set_selected_folder(Path(folder))

    def set_selected_folder(self, folder: Path) -> None:
        self._state.selected_folder = folder
        self._persist_last_scan_folder(folder)
        self.clear_scan_dependent_state()
        self._widgets.folder_label.setText(str(folder))
        self._widgets.library_guidance_label.setText(
            self._tr("Folder selected. Scan metadata to find complete Mixed In Key tracks.")
        )
        self._widgets.recommendation_guidance_label.setText(self._tr("Scan metadata before recommending a playlist."))
        self.refresh_idle_action_state()
        self._widgets.status_label.setText(self._tr("Folder selected"))
        self._sync_state()

    def _persist_last_scan_folder(self, folder: Path) -> None:
        settings = self._access.settings_getter()
        settings = settings.model_copy(
            update={"library": settings.library.model_copy(update={"last_scan_folder": folder})}
        )
        self._access.settings_setter(settings)
        if self._access.settings_repository is not None:
            self._access.settings_repository.save(settings)

    def populate_track_table(self, records: list[TrackRecord]) -> None:
        self._state.records_by_path = populate_library_table(
            self._widgets.library_screen.tracks_table,
            records,
            item_factory=_table_item,
            format_missing_metadata=_format_missing_metadata,
            format_track_tags=_format_track_tags,
            format_spectral_color=_format_spectral_color,
        )
        self._access.apply_song_filter(clear_selection=False)

    def apply_song_filter(self, query: str | None = None, *, clear_selection: bool = False) -> None:
        _layout.apply_main_song_filter(self, query, clear_selection=clear_selection)

    def selected_metadata_status_filter(self) -> str | None:
        status_text = self._widgets.metadata_screen.status_combo.currentText().casefold()
        return status_text if status_text in {"complete", "incomplete"} else None

    def selected_missing_metadata_filter(self) -> str | None:
        return _MISSING_METADATA_FILTERS.get(self._widgets.metadata_screen.missing_combo.currentText())

    def metadata_status_records(self, status: str) -> list[TrackRecord]:
        return metadata_status_records(self._state.scanned_records, status)

    def metadata_missing_field_records(self, missing_field: str) -> list[TrackRecord]:
        return metadata_missing_field_records(self._state.scanned_records, missing_field)

    def restore_persisted_tracks(self, records: list[TrackRecord]) -> None:
        if not records:
            self.refresh_idle_action_state()
            return
        self._state.scanned_records = records
        complete_count = sum(1 for record in records if record.metadata_status == "complete")
        incomplete_count = len(records) - complete_count
        self.populate_track_table(records)
        if self._state.selected_folder is None:
            self._widgets.folder_label.setText(self._tr("Library: saved"))
            self._widgets.folder_label.setToolTip(self._tr("Saved library loaded; no scan folder selected."))
            self._widgets.library_guidance_label.setText(
                self._tr("Use filters/search, select a complete track, then recommend.")
            )
            self._widgets.library_guidance_label.setToolTip(
                self._tr("Showing saved library from the app database. Choose a folder to re-scan or update metadata.")
            )
        else:
            self._widgets.folder_label.setText(self._tr("Library: saved folder"))
            self._widgets.folder_label.setToolTip(
                self._tr("Saved library loaded: {0}").format(self._state.selected_folder)
            )
            self._widgets.library_guidance_label.setText(
                self._tr("Use filters/search, select a complete track, then recommend.")
            )
            self._widgets.library_guidance_label.setToolTip(
                self._tr("Saved library loaded. Click Scan Metadata to refresh metadata from the last folder.")
            )
        self._widgets.recommendation_guidance_label.setText(self._tr(_RECOMMENDATION_READY_GUIDANCE))
        self._widgets.status_label.setText(
            self._tr("Loaded saved library: {0} complete, {1} incomplete").format(complete_count, incomplete_count)
        )
        self.refresh_idle_action_state()
        self._sync_state()
        self.start_spectral_completion_worker(records)

    def on_library_selection_changed(self, paths: list[str]) -> None:
        self._access.selected_paths[:] = paths
        self.refresh_idle_action_state()
        if self._audio_player._source_path is not None and self._audio_player._source_path not in paths:
            self._audio_player.stop()

    def on_metadata_export_requested(self, status_filter: str, missing_filter: str) -> None:
        missing_field = _MISSING_METADATA_FILTERS.get(missing_filter)
        norm_status = status_filter.casefold() if status_filter.casefold() in {"complete", "incomplete"} else None
        self._access.export_metadata_status_to_serato(status=norm_status, missing_field=missing_field)

    def on_exclude_requested(self) -> None:
        self._state.excluded_paths = self._state.excluded_paths | frozenset(self._access.selected_paths)
        self._sync_state()

    def on_lock_requested(self) -> None:
        self._state.locked_paths = self._state.locked_paths | frozenset(self._access.selected_paths)
        self._sync_state()

    def on_clear_constraints(self) -> None:
        self._state.excluded_paths = frozenset()
        self._state.locked_paths = frozenset()
        self._sync_state()

    def on_library_filters_cleared(self, active_labels: list[str]) -> None:
        from xfinaudio.desktop.undo_manager import Command

        labels = list(active_labels)
        self._access.undo_manager.push(
            Command(
                label=self._tr("Clear filters"),
                execute=lambda: self._widgets.library_screen.clear_quick_filters(emit_signal=False),
                undo=lambda: self._widgets.library_screen.restore_quick_filters(labels),
            )
        )
        self._access.refresh_undo_state()

    def on_proceed_to_export(self) -> None:
        if ReviewViewModel().can_export(self._state):
            self._access.workflow_tab_setter(3)

    def on_track_remove_requested(self, path: str) -> None:
        from xfinaudio.desktop.undo_manager import Command

        if path in self._state.playlist_removed_paths:
            return
        self.apply_track_removed(path)
        self._access.undo_manager.push(
            Command(
                label=self._tr("Remove {0}").format(Path(path).name),
                execute=lambda: self.apply_track_removed(path),
                undo=lambda: self.apply_track_restored(path),
            )
        )
        self._access.refresh_undo_state()

    def apply_track_removed(self, path: str) -> None:
        self._state.playlist_removed_paths = self._state.playlist_removed_paths | {path}
        self._sync_state()

    def apply_track_restored(self, path: str) -> None:
        self._state.playlist_removed_paths = self._state.playlist_removed_paths - {path}
        self._sync_state()

    def on_track_play_requested(self, path: str) -> None:
        try:
            self._access.open_track(path)
        except Exception as exc:
            self._log.warning("Could not open track %s: %s", path, exc)
            self._widgets.status_label.setText(self._tr("Could not open: {0}").format(Path(path).name))

    def on_preview_play_requested(self, path: str) -> None:
        self._audio_player.stop()
        self._audio_player.load(path)

    def on_live_load_next(self, path: str) -> None:
        self._access.live_load_next(path)

    def on_player_state_changed(self, state: object) -> None:
        from xfinaudio.desktop.audio_player_state import PlayerState

        if state == PlayerState.PLAYING:
            self._widgets.library_screen.set_playing_row(self._audio_player._source_path)
        elif state in (PlayerState.IDLE, PlayerState.ERROR):
            self._widgets.library_screen.set_playing_row(None)

    def on_player_error(self, message: str) -> None:
        self._log.warning("Audio preview error: %s", message)
        self._widgets.library_screen.set_playing_row(None)
        self._widgets.status_label.setText(self._tr("Preview error: {0}").format(message))

    def open_selected_library_track(self) -> None:
        selected_rows = sorted({index.row() for index in self._widgets.library_screen.tracks_table.selectedIndexes()})
        if not selected_rows:
            return
        path_item = self._widgets.library_screen.tracks_table.item(selected_rows[0], _TRACK_PATH_COLUMN)
        if path_item is not None:
            self.on_track_play_requested(path_item.text())

    def remove_selected_review_track(self) -> None:
        row = self._widgets.review_screen.recommendation_table.currentRow()
        path_item = self._widgets.review_screen.recommendation_table.item(row, 0)
        if path_item is not None and (path := path_item.data(Qt.ItemDataRole.UserRole)):
            self.on_track_remove_requested(path)

    def refresh_idle_action_state(self) -> None:
        self._widgets.library_screen.scan_button.setEnabled(self._state.selected_folder is not None)
        self._widgets.build_screen.recommend_button.setEnabled(self._access.selected_track_controls() is not None)
        status_filter = self.selected_metadata_status_filter()
        missing_filter = self.selected_missing_metadata_filter()
        self._widgets.metadata_screen.export_button.setEnabled(
            (missing_filter is not None and bool(self.metadata_missing_field_records(missing_filter)))
            or (status_filter is not None and bool(self.metadata_status_records(status_filter)))
        )
        self._widgets.library_screen.cancel_button.setEnabled(False)

    def show_tracks(
        self,
        records: list[TrackRecord],
        complete_count: int | None = None,
        incomplete_count: int | None = None,
    ) -> None:
        self.populate_track_table(records)
        if complete_count is None:
            complete_count = sum(1 for record in records if record.metadata_status == "complete")
        if incomplete_count is None:
            incomplete_count = len(records) - complete_count
        self._widgets.status_label.setText(
            self._tr("Scan complete: {0} complete, {1} incomplete").format(complete_count, incomplete_count)
        )
        self._sync_state()
        self.start_spectral_completion_worker(records)

    def start_spectral_completion_worker(self, records: list[TrackRecord]) -> None:
        missing = [record for record in records if record.spectral_profile is None]
        if not missing:
            return
        total_count = len(missing)
        self.cancel_spectral_completion_worker()
        self._replace_state(
            is_completing_spectral=True,
            spectral_progress_count=0,
            spectral_total_count=total_count,
        )
        self._sync_state()
        worker = SpectralCompletionWorker(parent=self._parent)
        worker.progress.connect(self.on_spectral_profile_ready)
        worker.progress_updated.connect(self.on_spectral_progress_updated)
        worker.finished.connect(self.on_spectral_completion_finished)
        worker.failed.connect(lambda error: self._log.error("Spectral completion failed: %s", error))
        self._spectral_completion_worker = worker
        worker.start(missing, self._workflow_service.repository)

    def cancel_spectral_completion_worker(self) -> None:
        if self._spectral_completion_worker is not None:
            self._spectral_completion_worker.cancel()
            self._spectral_completion_worker = None
        if self._state.is_completing_spectral:
            self._replace_state(
                is_completing_spectral=False,
                spectral_progress_count=0,
                spectral_total_count=0,
            )
            self._sync_state()

    def shutdown(self) -> None:
        """Cancel and wait for the spectral completion worker.

        Called automatically when the parent MainWindow is destroyed. Without
        this, the worker's QThread is destroyed while still running (librosa
        analysis does not cooperatively cancel mid-operation), and Qt prints
        "QThread: Destroyed while thread '' is still running" and aborts the
        process at interpreter exit (returncode 134).

        The cooperative ``cancel()`` asks the worker to stop and waits up to
        200ms. If the thread is still running after that, ``terminate()`` is
        used as a last resort to prevent the abort.
        """
        if self._spectral_completion_worker is not None:
            self._spectral_completion_worker.cancel()
            self._spectral_completion_worker.wait(200)
            if (
                self._spectral_completion_worker._thread is not None
                and self._spectral_completion_worker._thread.isRunning()
            ):
                self._spectral_completion_worker._thread.terminate()
                self._spectral_completion_worker._thread.wait(200)
            self._spectral_completion_worker = None

    @Slot(int, int)
    def on_spectral_progress_updated(self, processed_count: int, total_count: int) -> None:
        self._replace_state(
            is_completing_spectral=True,
            spectral_progress_count=processed_count,
            spectral_total_count=total_count,
        )
        self._sync_state()

    @Slot(str, object)
    def on_spectral_profile_ready(self, path: str, profile: object) -> None:
        for index, record in enumerate(self._state.scanned_records):
            if record.path == path:
                self._state.scanned_records[index] = record.model_copy(update={"spectral_profile": profile})
                break
        if path in self._state.records_by_path:
            existing = self._state.records_by_path[path]
            self._state.records_by_path[path] = existing.model_copy(update={"spectral_profile": profile})
        for row_index in range(self._widgets.library_screen.tracks_table.rowCount()):
            path_item = self._widgets.library_screen.tracks_table.item(row_index, _TRACK_PATH_COLUMN)
            if path_item is not None and path_item.text() == path:
                record = self._state.records_by_path.get(path)
                color_text = _format_spectral_color(record) if record is not None else ""
                self._widgets.library_screen.tracks_table.item(row_index, _TRACK_COLOR_COLUMN).setText(color_text)
                break
        self._sync_state()

    @Slot()
    def on_spectral_completion_finished(self) -> None:
        self._spectral_completion_worker = None
        self._replace_state(
            is_completing_spectral=False,
            spectral_progress_count=0,
            spectral_total_count=0,
        )
        self._sync_state()

    def _replace_state(self, **updates: object) -> None:
        self._state = self._state.model_copy(update=updates)
        self._access.state_setter(self._state)

    def clear_scan_dependent_state(self) -> None:
        self._state.scanned_records = []
        self._state.records_by_path = {}
        self._state.last_recommendation = None
        self._state.last_playlist_explanation = None
        self._state.last_quality_report = None
        self._state.last_dj_readiness_report = None
        self._state.last_prep_copilot_plan = None
        self._access.set_applied_copilot_variant(None)
        self._widgets.library_screen.tracks_table.setRowCount(0)
        self._widgets.library_screen.search_input.clear()
        self._widgets.review_screen.recommendation_table.setRowCount(0)
        self._access.set_recommendation_sections_expanded(False)
        self._access.clear_recommendation_review()
        self._widgets.export_screen.export_guidance_label.setText(
            self._tr(
                "Review recommendations before exporting. "
                "Serato export is enabled only after a recommendation is ready."
            )
        )
        self._sync_state()

    # Attributes/methods consumed by layout.apply_main_song_filter.
    @property
    def _library_screen(self) -> LibraryScreen:
        return self._widgets.library_screen

    @property
    def _metadata_screen(self) -> MetadataScreen:
        return self._widgets.metadata_screen

    @property
    def _records_by_path(self) -> dict[str, TrackRecord]:
        return self._state.records_by_path

    def _selected_metadata_status_filter(self) -> str | None:
        return self.selected_metadata_status_filter()

    def _selected_missing_metadata_filter(self) -> str | None:
        return self.selected_missing_metadata_filter()

    def _refresh_idle_action_state(self) -> None:
        self.refresh_idle_action_state()
