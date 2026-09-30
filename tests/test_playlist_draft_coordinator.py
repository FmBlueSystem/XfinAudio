"""Saved sets change only at the coordinator's explicit Save boundary."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.playlist_coordinator import PlaylistCoordinator
from xfinaudio.desktop.screens.my_playlists_screen import MyPlaylistsScreen
from xfinaudio.desktop.screens.playlist_editor import PlaylistEditor
from xfinaudio.desktop.undo_manager import UndoManager
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_repository import PlaylistRepository


def setup(qapp, tmp_path):
    repository = PlaylistRepository(tmp_path / "sets.db")
    playlist = repository.create("Saved", ["a", "b", "c"])
    host = SimpleNamespace(
        _playlist_repository=repository,
        _playlist_editor=PlaylistEditor(),
        _playlists_screen=MyPlaylistsScreen(),
        _review_screen=MagicMock(),
        _export_coordinator=MagicMock(),
        _undo_manager=UndoManager(),
        _undo_toolbar=MagicMock(),
        workflow_tabs=MagicMock(),
        _sync_state=MagicMock(),
        _show_playlist_editor=MagicMock(),
        tr=lambda t: t,
        _state=AppState(),
        scanned_records=[
            TrackRecord(path=p, energy_level=e, bpm=120, camelot_key="8A", metadata_status="complete")
            for p, e in (("a", 5), ("b", 2), ("c", 8))
        ],
    )
    coordinator = PlaylistCoordinator(host)
    coordinator.connect_signals()
    coordinator.open_playlist(playlist.id)
    return host, coordinator, playlist.id


def test_open_preview_confirm_remove_reorder_cancel_and_save(qapp, tmp_path):
    host, coordinator, id_ = setup(qapp, tmp_path)
    editor = host._playlist_editor
    host._show_playlist_editor.assert_called_once()
    editor.edit_input.setText("shorten to 2 tracks")
    editor.preview_button.click()
    assert host._playlist_repository.get_by_id(id_).track_paths == ["a", "b", "c"]
    editor.confirm_button.click()
    assert editor._track_paths == ["a", "b"]
    assert host._playlist_repository.get_by_id(id_).track_paths == ["a", "b", "c"]
    editor._on_remove_clicked(0)
    assert host._playlist_repository.get_by_id(id_).track_paths == ["a", "b", "c"]
    editor.cancel_button.click()
    editor.tracks_table.selectRow(1)
    editor.move_up_button.click()
    assert editor._track_paths == ["b", "a", "c"]
    assert host._playlist_repository.get_by_id(id_).track_paths == ["a", "b", "c"]
    host._undo_manager.undo()
    assert editor._track_paths == ["a", "b", "c"]
    host._undo_manager.redo()
    editor.save_button.click()
    assert host._playlist_repository.get_by_id(id_).track_paths == ["b", "a", "c"]
    assert not editor.is_dirty


def test_changed_constraints_invalidate_preview_and_block_unsafe_save(qapp, tmp_path):
    host, coordinator, id_ = setup(qapp, tmp_path)
    editor = host._playlist_editor
    editor.edit_input.setText("shorten to 2 tracks")
    editor.preview_button.click()
    host._state = host._state.model_copy(update={"locked_paths": frozenset({"c"})})
    editor.confirm_button.click()
    assert editor._track_paths == ["a", "b", "c"]
    editor._on_remove_clicked(2)
    host._state = host._state.model_copy(update={"excluded_paths": frozenset({"b"})})
    editor.save_button.click()
    assert host._playlist_repository.get_by_id(id_).track_paths == ["a", "b", "c"]
    assert "excluded" in editor.status_label.text()


def test_external_edit_blocks_save_and_old_undo_cannot_modify_another_set(qapp, tmp_path):
    host, coordinator, id_ = setup(qapp, tmp_path)
    editor = host._playlist_editor
    editor.tracks_table.selectRow(1)
    editor.move_up_button.click()
    host._playlist_repository.update_tracks(id_, ["c"])
    editor.save_button.click()
    assert host._playlist_repository.get_by_id(id_).track_paths == ["c"]
    assert "changed" in editor.status_label.text()
    other = host._playlist_repository.create("Other", ["x"])
    editor.cancel_button.click()
    coordinator.open_playlist(other.id)
    host._undo_manager.undo()
    assert editor._track_paths == ["x"]
    coordinator.delete_playlist(other.id)
    assert editor._playlist_id is None


def test_dirty_open_is_blocked_and_explicit_discard_allows_navigation(qapp, tmp_path):
    host, coordinator, id_ = setup(qapp, tmp_path)
    editor = host._playlist_editor
    editor._on_remove_clicked(0)
    other = host._playlist_repository.create("Other", ["x"])
    coordinator.open_playlist(other.id)
    assert editor._playlist_id == id_
    assert editor._track_paths == ["b", "c"]
    assert "discard" in editor.status_label.text()
    editor.back_button.click()
    host.workflow_tabs.setCurrentIndex.assert_called_with(4)
    assert editor._track_paths == ["b", "c"]
    editor.cancel_button.click()
    coordinator.open_playlist(other.id)
    assert editor._playlist_id == other.id


def test_repository_change_invalidates_preview_before_confirmation(qapp, tmp_path):
    host, coordinator, id_ = setup(qapp, tmp_path)
    editor = host._playlist_editor
    editor.edit_input.setText("shorten to 2 tracks")
    editor.preview_button.click()
    host._playlist_repository.update_tracks(id_, ["c"])
    editor.confirm_button.click()
    assert editor._track_paths == ["a", "b", "c"]
    assert not editor.confirm_button.isEnabled()
    assert "changed" in editor.status_label.text()
