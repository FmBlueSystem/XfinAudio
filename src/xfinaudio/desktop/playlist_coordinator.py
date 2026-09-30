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
import re
from typing import Any, Protocol

from xfinaudio.application.playlist_edit_intents import normalize_request, validate_edit
from xfinaudio.application.saved_playlist_assistant import compare_saved_sets, describe_saved_set, search_saved_sets
from xfinaudio.application.saved_playlists import SavedPlaylistService
from xfinaudio.desktop.app_state_transitions import apply_saved_playlist_export_recommendation
from xfinaudio.desktop.undo_manager import Command, UndoManager
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_models import Playlist
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
    def _show_playlist_editor(self) -> None: ...


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
        screen.query_requested.connect(self.search_saved_playlists)
        screen.compare_requested.connect(self.compare_saved_playlists)
        screen.open_requested.connect(self.open_playlist)
        screen.create_requested.connect(self.create_playlist)
        screen.rename_requested.connect(self.rename_playlist)
        screen.duplicate_requested.connect(self.duplicate_playlist)
        screen.delete_requested.connect(self.delete_playlist)

        editor = host._playlist_editor
        editor.back_requested.connect(lambda: host.workflow_tabs.setCurrentIndex(4))
        editor.preview_requested.connect(self.preview_edit)
        editor.confirm_requested.connect(self.confirm_edit)
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
        self._refresh_editor_context()
        self._host._sync_state()
        show_editor = getattr(self._host, "_show_playlist_editor", None)
        if show_editor is not None:
            show_editor()

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
        if host._playlist_editor._playlist_id == playlist_id:
            host._playlist_editor.clear_playlist()
            host.workflow_tabs.setCurrentIndex(4)
        self.refresh_list()
        host._sync_state()

    def save_playlist(self, playlist_id: int, track_paths: list[str]) -> None:
        """Persist the editor's current track order and refresh the list."""
        host = self._host
        editor = host._playlist_editor
        current = host._playlist_repository.get_by_id(playlist_id)
        if editor._playlist_id != playlist_id or track_paths != editor._track_paths:
            return
        if current is None or tuple(current.track_paths) != editor._saved_paths:
            editor.status_label.setText(host.tr("Saved playlist changed or was deleted. Reopen it before saving."))
            return
        self._refresh_editor_context()
        try:
            validate_edit(
                editor._saved_paths,
                track_paths,
                locked_paths=editor._locked_paths,
                excluded_paths=editor._excluded_paths,
            )
        except ValueError as error:
            editor.status_label.setText(str(error))
            return
        self._service.save_track_order(playlist_id, track_paths)
        saved = host._playlist_repository.get_by_id(playlist_id)
        if saved is not None:
            editor.set_playlist(saved)
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
        if host._playlist_editor._playlist_id == playlist_id and host._playlist_editor.is_dirty is True:
            host._playlist_editor.status_label.setText(host.tr("Save or discard this draft before exporting."))
            return
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

    def _refresh_editor_context(self) -> None:
        host = self._host
        state = getattr(host, "_state", None)
        host._playlist_editor.set_context(
            host.scanned_records,
            locked_paths=getattr(state, "locked_paths", frozenset()),
            excluded_paths=getattr(state, "excluded_paths", frozenset()),
        )

    def preview_edit(self, request: str) -> None:
        self._refresh_editor_context()
        self._host._playlist_editor.preview_edit(request)

    def confirm_edit(self) -> None:
        self._refresh_editor_context()
        self._host._playlist_editor.confirm_preview()

    def remove_track(self, path: str) -> None:
        """Removal is draft-only; Save is the sole persistence boundary."""
        self._host._sync_state()

    def refresh_list(self) -> None:
        """Repopulate MyPlaylistsScreen with current repository summaries."""
        summaries = self._host._playlist_repository.list_summaries()
        self._host._playlists_screen.populate_list(summaries)

    def _on_tracks_reordered(self, track_paths: list[str]) -> None:
        """Record a reversible draft reorder, never a hidden repository write."""
        editor = self._host._playlist_editor
        playlist_id = editor._playlist_id
        if playlist_id is None:
            return
        previous_paths = list(editor._track_paths)
        new_paths = list(track_paths)
        revision = editor.session_revision
        if not self._apply_track_order(playlist_id, new_paths, revision):
            return
        self._host._undo_manager.push(
            Command(
                label=self._host.tr("Reorder playlist"),
                execute=lambda: self._apply_track_order(playlist_id, new_paths, revision),
                undo=lambda: self._apply_track_order(playlist_id, previous_paths, revision),
            )
        )
        self._host._undo_toolbar.refresh()

    def _apply_track_order(self, playlist_id: int, track_paths: list[str], revision: int) -> bool:
        """Session-bound undo cannot edit another playlist or cross a save/cancel."""
        editor = self._host._playlist_editor
        if editor._playlist_id != playlist_id or editor.session_revision != revision:
            return False
        self._refresh_editor_context()
        if not editor.apply_order(track_paths):
            return False
        self._host._sync_state()
        return True

    def _saved_sets(self) -> list[Playlist]:
        repository = self._host._playlist_repository
        return [p for s in repository.list_summaries() if (p := repository.get_by_id(s.id)) is not None]

    def search_saved_playlists(self, request: str) -> None:
        playlists = self._saved_sets()
        text = normalize_request(request)
        if text.startswith(("compare ", "compara ")):
            names = re.split(r"\s+(?:and|y|vs)\s+", text.split(" ", 1)[1])
            matches = [[p for p in playlists if normalize_request(p.name) == name] for name in names]
            if len(names) < 2 or any(len(group) != 1 for group in matches):
                self._host._playlists_screen.assistant_output.setPlainText(
                    "Playlist names not found or ambiguous. Select at least two saved sets and use Compare selected."
                )
                return
            self.compare_saved_playlists([group[0].id for group in matches])
            return
        result = search_saved_sets(request, playlists, self._host.scanned_records)
        description = "\n".join(describe_saved_set(p, self._host.scanned_records) for p in result)
        self._host._playlists_screen.show_assistant_result(
            result, description or "No saved playlists match. Search actual names, genres or track metadata."
        )

    def compare_saved_playlists(self, ids: list[int]) -> None:
        playlists = [p for p in self._saved_sets() if p.id in ids]
        try:
            description = compare_saved_sets(playlists, self._host.scanned_records)
        except ValueError as error:
            self._host._playlists_screen.assistant_output.setPlainText(str(error))
            return
        self._host._playlists_screen.show_assistant_result(playlists, description)
