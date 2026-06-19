"""Playlist coordination logic: a Qt-aware orchestrator extracted from MainWindow.

``PlaylistCoordinator`` owns the Qt signal wiring and presentation-side
coordination between ``MyPlaylistsScreen`` / ``PlaylistEditor`` and the
saved-playlist application service. It reads state and widgets through a
structural ``host`` handle (the ``MainWindow``), mirroring the
``ExportCoordinator`` / ``ExportHost`` precedent.

The playlist screen signals were previously UNWIRED in ``MainWindow``; this
coordinator is the wiring home (see ``connect_signals``), not ``MainWindow``.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from xfinaudio.application.saved_playlists import SavedPlaylistService
from xfinaudio.desktop.app_state_transitions import apply_saved_playlist_export_recommendation
from xfinaudio.desktop.undo_manager import Command, UndoManager
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.ports import PlaylistRepositoryPort
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation

LOGGER = logging.getLogger(__name__)


class PlaylistHost(Protocol):
    """Structural host boundary for ``PlaylistCoordinator``.

    Declares only the ``MainWindow`` members the coordinator reads or calls,
    decoupling playlist orchestration from the concrete window type.
    """

    _playlist_repository: PlaylistRepositoryPort
    _review_screen: Any
    _playlists_screen: Any
    _playlist_editor: Any
    _export_coordinator: Any
    _undo_manager: UndoManager
    _undo_toolbar: Any
    workflow_tabs: Any
    last_recommendation: PlaylistRecommendation | None
    scanned_records: list[TrackRecord]

    def tr(self, text: str) -> str: ...
    def _replace_app_state(self, state: Any) -> None: ...
    def _sync_state(self) -> None: ...


class PlaylistCoordinator:
    """Qt-aware playlist orchestration extracted from MainWindow.

    State and widget access flow through ``host`` (the ``MainWindow``);
    saved-playlist persistence decisions are delegated to ``SavedPlaylistService``.
    """

    def __init__(self, host: PlaylistHost) -> None:
        self._host = host
        self._service = SavedPlaylistService(repository=host._playlist_repository)

    def connect_signals(self) -> None:
        """Wire all MyPlaylistsScreen and PlaylistEditor signals (net-new wiring)."""
        host = self._host
        screen = host._playlists_screen
        screen.open_requested.connect(self.open_playlist)
        screen.create_requested.connect(self.create_playlist)
        screen.rename_requested.connect(self.rename_playlist)
        screen.duplicate_requested.connect(self.duplicate_playlist)
        screen.delete_requested.connect(self.delete_playlist)

        editor = host._playlist_editor
        editor.track_removed.connect(self.remove_track)
        editor.tracks_reordered.connect(self._on_tracks_reordered)
        editor.export_requested.connect(self.export_playlist)
        editor.save_requested.connect(self.save_playlist)
        host._review_screen.save_to_playlists_requested.connect(self.save_recommendation)

    def open_playlist(self, playlist_id: int) -> None:
        """Load a saved playlist into the editor."""
        playlist = self._host._playlist_repository.get_by_id(playlist_id)
        if playlist is None:
            LOGGER.warning("Playlist %s not found on open", playlist_id)
            return
        self._host._playlist_editor.set_playlist(playlist)

    def create_playlist(self) -> None:
        """Create a new empty playlist and refresh the list."""
        host = self._host
        self._service.create_empty_playlist(host.tr("New Playlist"))
        self.refresh_list()
        host._sync_state()

    def rename_playlist(self, playlist_id: int, name: str) -> None:
        """Rename a playlist and refresh the list."""
        if not name:
            return
        host = self._host
        self._service.rename_playlist(playlist_id, name)
        self.refresh_list()
        host._sync_state()

    def duplicate_playlist(self, playlist_id: int) -> None:
        """Duplicate a playlist and refresh the list."""
        host = self._host
        self._service.duplicate_playlist(playlist_id)
        self.refresh_list()
        host._sync_state()

    def delete_playlist(self, playlist_id: int) -> None:
        """Delete a playlist and refresh the list."""
        host = self._host
        self._service.delete_playlist(playlist_id)
        self.refresh_list()
        host._sync_state()

    def save_playlist(self, playlist_id: int, track_paths: list[str]) -> None:
        """Persist the editor's current track order and refresh the list."""
        host = self._host
        self._service.save_track_order(playlist_id, track_paths)
        self.refresh_list()
        host._sync_state()

    def save_recommendation(self, name: str | None = None) -> None:
        """Persist the current generated recommendation as a saved playlist."""
        host = self._host
        recommendation = host.last_recommendation
        if recommendation is None:
            return
        self._service.save_recommendation(recommendation, name=name)
        self.refresh_list()
        host.workflow_tabs.setCurrentIndex(4)
        host._sync_state()

    def export_playlist(self, playlist_id: int) -> None:
        """Load the requested playlist and run the normal Serato export flow."""
        host = self._host
        export = self._service.build_export_recommendation(playlist_id, host.scanned_records)
        if export is None:
            LOGGER.warning("Playlist %s not found on export", playlist_id)
            return
        host._playlist_editor.set_playlist(export.playlist)
        if hasattr(host, "_replace_app_state") and hasattr(host, "_state"):
            host._replace_app_state(apply_saved_playlist_export_recommendation(host._state, export.recommendation))
        else:
            host.last_recommendation = export.recommendation
        host._export_coordinator.export_recommendation_to_serato(crate_name=export.playlist.name)

    def remove_track(self, path: str) -> None:
        """Persist a track removal performed in the editor."""
        editor = self._host._playlist_editor
        playlist_id = editor._playlist_id
        if playlist_id is None:
            return
        self._service.save_track_order(playlist_id, list(editor._track_paths))
        self.refresh_list()
        self._host._sync_state()

    def refresh_list(self) -> None:
        """Repopulate MyPlaylistsScreen with current repository summaries."""
        summaries = self._host._playlist_repository.list_summaries()
        self._host._playlists_screen.populate_list(summaries)

    def _on_tracks_reordered(self, track_paths: list[str]) -> None:
        """Persist a reorder performed in the editor."""
        editor = self._host._playlist_editor
        playlist_id = editor._playlist_id
        if playlist_id is None:
            return
        previous_paths = list(editor._track_paths)
        new_paths = list(track_paths)
        self._apply_track_order(playlist_id, new_paths)
        self._host._undo_manager.push(
            Command(
                label=self._host.tr("Reorder playlist"),
                execute=lambda: self._apply_track_order(playlist_id, new_paths),
                undo=lambda: self._apply_track_order(playlist_id, previous_paths),
            )
        )
        self._host._undo_toolbar.refresh()

    def _apply_track_order(self, playlist_id: int, track_paths: list[str]) -> None:
        """Persist and render an editor track order without recording a new command."""
        editor = self._host._playlist_editor
        editor._track_paths = list(track_paths)
        editor._populate_table()
        self._service.save_track_order(playlist_id, track_paths)
        self.refresh_list()
        self._host._sync_state()
