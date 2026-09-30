"""Tests for MyPlaylistsScreen."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QMessageBox

from xfinaudio.desktop.screens.my_playlists_screen import MyPlaylistsScreen
from xfinaudio.library.playlist_models import PlaylistSummary
from xfinaudio.library.playlist_repository import PlaylistRepository


class TestConstruction:
    def test_can_construct(self, qapp: QApplication) -> None:
        screen = MyPlaylistsScreen()
        assert screen is not None


class TestPopulateList:
    def test_populate_list_shows_playlists(self, qapp: QApplication) -> None:
        screen = MyPlaylistsScreen()
        summaries = [
            PlaylistSummary(id=1, name="Set A", track_count=5, updated_at=datetime(2026, 6, 8)),
        ]
        screen.populate_list(summaries)
        assert screen.list_widget.count() == 1

    def test_populate_list_empty(self, qapp: QApplication) -> None:
        screen = MyPlaylistsScreen()
        screen.populate_list([])
        assert screen.list_widget.count() == 0


class TestSignals:
    def test_double_click_emits_open_requested(self, qapp: QApplication) -> None:
        screen = MyPlaylistsScreen()
        ids: list[int] = []
        screen.open_requested.connect(ids.append)
        screen.populate_list([PlaylistSummary(id=1, name="Set A", track_count=5, updated_at=datetime(2026, 6, 8))])
        screen._on_item_activated(screen.list_widget.item(0))
        assert ids == [1]

    def test_create_button_emits_create_requested(self, qapp: QApplication) -> None:
        screen = MyPlaylistsScreen()
        calls: list[None] = []
        screen.create_requested.connect(lambda: calls.append(None))
        screen._on_create_clicked()
        assert len(calls) == 1

    def test_rename_click_prompts_and_emits_confirmed_non_empty_name(self, qapp: QApplication) -> None:
        screen = MyPlaylistsScreen()
        emitted: list[tuple[int, str]] = []
        screen.rename_requested.connect(lambda playlist_id, name: emitted.append((playlist_id, name)))
        screen.populate_list([PlaylistSummary(id=7, name="Old", track_count=3, updated_at=datetime(2026, 6, 8))])
        screen.list_widget.setCurrentRow(0)

        with patch(
            "xfinaudio.desktop.screens.my_playlists_screen.QInputDialog.getText",
            return_value=("New Name", True),
        ) as get_text:
            screen._on_rename_clicked()

        get_text.assert_called_once()
        assert get_text.call_args.args[3] == QLineEdit.EchoMode.Normal
        assert emitted == [(7, "New Name")]

    def test_rename_click_ignores_cancelled_or_blank_names(self, qapp: QApplication) -> None:
        screen = MyPlaylistsScreen()
        emitted: list[tuple[int, str]] = []
        screen.rename_requested.connect(lambda playlist_id, name: emitted.append((playlist_id, name)))
        screen.populate_list([PlaylistSummary(id=7, name="Old", track_count=3, updated_at=datetime(2026, 6, 8))])
        screen.list_widget.setCurrentRow(0)

        with patch("xfinaudio.desktop.screens.my_playlists_screen.QInputDialog.getText", return_value=("", True)):
            screen._on_rename_clicked()
        with patch("xfinaudio.desktop.screens.my_playlists_screen.QInputDialog.getText", return_value=("New", False)):
            screen._on_rename_clicked()

        assert emitted == []


@pytest.mark.parametrize("answer", [QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.NoButton])
def test_delete_cancel_or_close_preserves_synthetic_saved_set(qapp, tmp_path, monkeypatch, answer):
    screen, repository, selected, other = deletion_screen(tmp_path)
    assert selected.id is not None and other.id is not None
    prompts = []

    def confirm(dialog):
        prompts.append(dialog)
        return int(answer)

    monkeypatch.setattr(QMessageBox, "exec", confirm)
    screen.delete_button.click()
    assert len(prompts) == 1
    dialog = prompts[0]
    assert dialog.textFormat() == Qt.TextFormat.PlainText
    assert selected.name in dialog.text()
    assert "permanently" in dialog.text()
    assert "cannot be undone" in dialog.text()
    assert dialog.defaultButton() == dialog.button(QMessageBox.StandardButton.Cancel)
    assert repository.get_by_id(selected.id) == selected
    assert repository.get_by_id(other.id) == other


def test_delete_acceptance_removes_only_named_synthetic_set(qapp, tmp_path, monkeypatch):
    screen, repository, selected, other = deletion_screen(tmp_path)
    assert selected.id is not None and other.id is not None
    prompts = []

    def confirm(dialog):
        prompts.append(dialog)
        return int(QMessageBox.StandardButton.Discard)

    monkeypatch.setattr(QMessageBox, "exec", confirm)
    screen.delete_button.click()
    assert len(prompts) == 1
    assert selected.name in prompts[0].text()
    assert prompts[0].button(QMessageBox.StandardButton.Discard).text() == "Delete"
    assert repository.get_by_id(selected.id) is None
    assert repository.get_by_id(other.id) == other


def test_delete_without_selection_does_not_prompt_or_emit(qapp, monkeypatch):
    screen = MyPlaylistsScreen()
    emitted = []
    screen.delete_requested.connect(emitted.append)
    with patch.object(QMessageBox, "exec") as prompt:
        screen.delete_button.click()
    prompt.assert_not_called()
    assert emitted == []


def deletion_screen(tmp_path):
    repository = PlaylistRepository(tmp_path / "synthetic-sets.db")
    selected = repository.create("Selected  (warm) <b>set</b>", ["synthetic.wav"])
    other = repository.create("Keep this set", ["other-synthetic.wav"])
    screen = MyPlaylistsScreen()
    screen.populate_list(repository.list_summaries())
    selected_row = next(
        row
        for row in range(screen.list_widget.count())
        if screen.list_widget.item(row).data(Qt.ItemDataRole.UserRole) == selected.id
    )
    screen.list_widget.setCurrentRow(selected_row)
    screen.delete_requested.connect(repository.delete)
    return screen, repository, selected, other


def test_delete_dialog_enter_activates_default_cancel(qapp, tmp_path, monkeypatch):
    screen, repository, selected, other = deletion_screen(tmp_path)
    assert selected.id is not None and other.id is not None
    real_exec = QMessageBox.exec

    def confirm(dialog):
        QTimer.singleShot(0, lambda: QTest.keyClick(dialog, Qt.Key.Key_Return))
        return real_exec(dialog)

    monkeypatch.setattr(QMessageBox, "exec", confirm)
    screen.delete_button.click()
    assert repository.get_by_id(selected.id) == selected
    assert repository.get_by_id(other.id) == other


@pytest.mark.parametrize("key", [Qt.Key.Key_Return, Qt.Key.Key_Enter])
def test_saved_list_consumes_activation_key_once(qapp, key):
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QKeyEvent

    screen = MyPlaylistsScreen()
    screen.populate_list([PlaylistSummary(1, "Synthetic", 2, datetime(2026, 9, 30))])
    opened = []
    screen.open_requested.connect(opened.append)
    screen.show()
    screen.list_widget.setCurrentRow(0)
    screen.list_widget.setFocus()
    qapp.processEvents()
    try:
        event = QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier)
        event.ignore()
        qapp.sendEvent(screen.list_widget, event)
        assert event.isAccepted(), "activation must not leak to a parent/default button"
        assert opened == [1]
        repeated = QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier, "", True)
        qapp.sendEvent(screen.list_widget, repeated)
        assert opened == [1], "holding the activation key must not reopen the editor"
    finally:
        screen.close()


def test_saved_list_double_click_opens_once_and_arrows_still_navigate(qapp):
    screen = MyPlaylistsScreen()
    screen.populate_list([PlaylistSummary(i, f"Set {i}", 2, datetime(2026, 9, 30)) for i in (1, 2)])
    opened = []
    screen.open_requested.connect(opened.append)
    screen.show()
    screen.list_widget.setCurrentRow(0)
    screen.list_widget.setFocus()
    qapp.processEvents()
    try:
        QTest.keyClick(screen.list_widget, Qt.Key.Key_Down)
        assert screen.selected_playlist_id() == 2
        assert opened == []
        pos = screen.list_widget.visualItemRect(screen.list_widget.item(1)).center()
        QTest.mouseClick(screen.list_widget.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        QTest.mouseDClick(screen.list_widget.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        assert opened == [2]
    finally:
        screen.close()


def test_saved_list_empty_and_search_return_do_not_open_a_playlist(qapp):
    screen = MyPlaylistsScreen()
    opened, searches = [], []
    screen.open_requested.connect(opened.append)
    screen.query_requested.connect(searches.append)
    screen.show()
    qapp.processEvents()
    try:
        QTest.keyClick(screen.list_widget, Qt.Key.Key_Return)
        screen.query_input.setText("find house")
        QTest.keyClick(screen.query_input, Qt.Key.Key_Return)
        assert searches == ["find house"]
        assert opened == []
    finally:
        screen.close()
