"""Actual editor controls keep proposals and drafts separate from Save."""

from datetime import datetime

from PySide6.QtWidgets import QPushButton

from xfinaudio.desktop.screens.playlist_editor import PlaylistEditor
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_models import Playlist


def editor(qapp):
    widget = PlaylistEditor()
    widget.set_playlist(Playlist(1, "<Set>", datetime.now(), datetime.now(), ["a", "b", "c"]))
    widget.set_context(
        [TrackRecord(path=p, title=p.upper(), energy_level=e) for p, e in (("a", 5), ("b", 2), ("c", 8))]
    )
    widget.preview_requested.connect(widget.preview_edit)
    widget.confirm_requested.connect(widget.confirm_preview)
    widget.tracks_reordered.connect(widget.apply_order)
    return widget


def test_preview_confirm_and_cancel_are_separate_draft_actions(qapp):
    widget = editor(qapp)
    saves = []
    widget.save_requested.connect(lambda *args: saves.append(args))
    widget.edit_input.setText("shorten to 2 tracks")
    widget.preview_button.click()
    assert widget._track_paths == ["a", "b", "c"]
    assert "A" in widget.preview_text.toPlainText()
    widget.confirm_button.click()
    assert widget._track_paths == ["a", "b"]
    assert saves == []
    assert not widget.export_button.isEnabled()
    widget.cancel_button.click()
    assert widget._track_paths == ["a", "b", "c"]
    assert widget.export_button.isEnabled()


def test_manual_remove_invalidates_preview_and_locked_removal_is_blocked(qapp):
    widget = editor(qapp)
    widget.set_context(widget._records, locked_paths=frozenset({"a"}))
    widget.edit_input.setText("shorten to 2 tracks")
    widget.preview_button.click()
    button = widget.tracks_table.cellWidget(0, 4)
    assert isinstance(button, QPushButton)
    button.click()
    assert widget._track_paths == ["a", "b", "c"]
    widget._on_remove_clicked(1)
    widget.confirm_button.click()
    assert widget._track_paths == ["a", "c"]
    assert not widget.confirm_button.isEnabled()


def test_context_change_and_cancel_preview_prevent_stale_confirmation(qapp):
    widget = editor(qapp)
    widget.edit_input.setText("raise energy")
    widget.preview_button.click()
    widget.set_context(widget._records, excluded_paths=frozenset({"b"}))
    widget.confirm_button.click()
    assert widget._track_paths == ["a", "b", "c"]
    widget.preview_button.click()
    widget.cancel_preview_button.click()
    widget.confirm_button.click()
    assert widget._track_paths == ["a", "b", "c"]


def test_move_controls_reorder_draft_and_save_only_emits_on_click(qapp):
    widget = editor(qapp)
    saves = []
    widget.save_requested.connect(lambda *args: saves.append(args))
    widget.tracks_table.selectRow(1)
    widget.move_up_button.click()
    assert widget._track_paths == ["b", "a", "c"]
    assert saves == []
    widget.save_button.click()
    assert saves == [(1, ["b", "a", "c"])]
