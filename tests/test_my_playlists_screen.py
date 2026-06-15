"""Tests for MyPlaylistsScreen."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QLineEdit

from xfinaudio.desktop.screens.my_playlists_screen import MyPlaylistsScreen
from xfinaudio.library.playlist_models import PlaylistSummary


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
