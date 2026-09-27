"""Tests for the window factory's playlist database path resolution."""

from __future__ import annotations

from pathlib import Path

from xfinaudio.desktop import window_factory
from xfinaudio.desktop.window_factory import playlist_repository_for


def test_fallback_playlist_repository_lives_in_the_app_data_directory(monkeypatch) -> None:
    """A repository without db_path must not scatter playlists.db into the cwd."""
    fake_home = Path("/tmp/fake-home")
    monkeypatch.setattr(window_factory, "default_database_path", lambda: fake_home / ".xfinaudio" / "xfinaudio.sqlite3")
    monkeypatch.chdir("/tmp")

    repository = playlist_repository_for(None)

    assert repository.db_path == fake_home / ".xfinaudio" / "playlists.db"


def test_explicit_repository_db_path_still_derives_the_playlist_database(monkeypatch, tmp_path: Path) -> None:
    """A repository that knows its db_path keeps deriving the sibling playlists.db."""
    fake_home = Path("/tmp/fake-home")
    monkeypatch.setattr(window_factory, "default_database_path", lambda: fake_home / ".xfinaudio" / "xfinaudio.sqlite3")

    class Repository:
        db_path = tmp_path / "library.sqlite3"

    repository = playlist_repository_for(Repository())

    assert repository.db_path == tmp_path / "playlists.db"
