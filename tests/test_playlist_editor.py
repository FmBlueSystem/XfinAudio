"""Tests for PlaylistEditor widget."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import QApplication

from xfinaudio.desktop.screens.playlist_editor import PlaylistEditor
from xfinaudio.library.playlist_models import Playlist


class TestConstruction:
    def test_can_construct(self, qapp: QApplication) -> None:
        editor = PlaylistEditor()
        assert editor is not None


class TestSetPlaylist:
    def test_set_playlist_populates_table(self, qapp: QApplication) -> None:
        editor = PlaylistEditor()
        playlist = Playlist(
            id=1,
            name="Set A",
            created_at=datetime(2026, 6, 8),
            updated_at=datetime(2026, 6, 8),
            track_paths=["/music/a.flac", "/music/b.flac"],
        )
        editor.set_playlist(playlist)
        assert editor.tracks_table.rowCount() == 2


class TestRemoveTrack:
    def test_remove_row_emits_track_removed(self, qapp: QApplication) -> None:
        editor = PlaylistEditor()
        playlist = Playlist(
            id=1,
            name="Set A",
            created_at=datetime(2026, 6, 8),
            updated_at=datetime(2026, 6, 8),
            track_paths=["/music/a.flac", "/music/b.flac"],
        )
        editor.set_playlist(playlist)
        removed: list[str] = []
        editor.track_removed.connect(removed.append)
        editor._on_remove_clicked(0)
        assert removed == ["/music/a.flac"]


class TestSignals:
    def test_export_requested_emits(self, qapp: QApplication) -> None:
        editor = PlaylistEditor()
        playlist = Playlist(
            id=42,
            name="Set A",
            created_at=datetime(2026, 6, 8),
            updated_at=datetime(2026, 6, 8),
            track_paths=["/music/a.flac"],
        )
        editor.set_playlist(playlist)
        ids: list[int] = []
        editor.export_requested.connect(ids.append)
        editor._on_export_clicked()
        assert len(ids) == 1
