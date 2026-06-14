"""Playlist coordination logic: a Qt-aware orchestrator extracted from MainWindow.

``PlaylistCoordinator`` owns the playlist CRUD orchestration and the signal
wiring between ``MyPlaylistsScreen`` / ``PlaylistEditor`` and the
``PlaylistRepository``. It reads state and widgets through a structural
``host`` handle (the ``MainWindow``), mirroring the ``ExportCoordinator`` /
``ExportHost`` precedent.

The playlist screen signals were previously UNWIRED in ``MainWindow``; this
coordinator is the wiring home (see ``connect_signals``), not ``MainWindow``.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from xfinaudio.library.playlist_repository import PlaylistRepository

LOGGER = logging.getLogger(__name__)


class PlaylistHost(Protocol):
    """Structural host boundary for ``PlaylistCoordinator``.

    Declares only the ``MainWindow`` members the coordinator reads or calls,
    decoupling playlist orchestration from the concrete window type.
    """

    _playlist_repository: PlaylistRepository
    _playlists_screen: Any
    _playlist_editor: Any
    workflow_tabs: Any

    def tr(self, text: str) -> str: ...
    def _sync_state(self) -> None: ...


class PlaylistCoordinator:
    """Qt-aware playlist orchestration extracted from MainWindow.

    State and widget access flow through ``host`` (the ``MainWindow``);
    persistence is delegated to ``host._playlist_repository``.
    """

    def __init__(self, host: PlaylistHost) -> None:
        self._host = host

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
        host._playlist_repository.create(host.tr("New Playlist"), [])
        self.refresh_list()
        host._sync_state()

    def rename_playlist(self, playlist_id: int, name: str) -> None:
        """Rename a playlist and refresh the list."""
        if not name:
            return
        host = self._host
        host._playlist_repository.update_name(playlist_id, name)
        self.refresh_list()
        host._sync_state()

    def duplicate_playlist(self, playlist_id: int) -> None:
        """Duplicate a playlist and refresh the list."""
        host = self._host
        host._playlist_repository.duplicate(playlist_id)
        self.refresh_list()
        host._sync_state()

    def delete_playlist(self, playlist_id: int) -> None:
        """Delete a playlist and refresh the list."""
        host = self._host
        host._playlist_repository.delete(playlist_id)
        self.refresh_list()
        host._sync_state()

    def save_playlist(self, playlist_id: int, track_paths: list[str]) -> None:
        """Persist the editor's current track order and refresh the list."""
        host = self._host
        host._playlist_repository.update_tracks(playlist_id, track_paths)
        self.refresh_list()
        host._sync_state()

    def export_playlist(self, playlist_id: int) -> None:
        """Load the requested playlist into the editor for export review."""
        playlist = self._host._playlist_repository.get_by_id(playlist_id)
        if playlist is None:
            LOGGER.warning("Playlist %s not found on export", playlist_id)
            return
        self._host._playlist_editor.set_playlist(playlist)

    def remove_track(self, path: str) -> None:
        """Persist a track removal performed in the editor."""
        editor = self._host._playlist_editor
        playlist_id = editor._playlist_id
        if playlist_id is None:
            return
        self._host._playlist_repository.update_tracks(playlist_id, list(editor._track_paths))
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
        self._host._playlist_repository.update_tracks(playlist_id, track_paths)
        self.refresh_list()
        self._host._sync_state()
