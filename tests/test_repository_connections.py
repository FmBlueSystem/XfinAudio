"""Operation-local SQLite connection ownership, independent of garbage collection."""

import sqlite3

import pytest

from xfinaudio.library.playlist_repository import PlaylistRepository
from xfinaudio.library.track_repository import TrackRepository


@pytest.mark.parametrize("repository_class", [PlaylistRepository, TrackRepository])
def test_connections_close_after_reads_writes_and_errors(tmp_path, monkeypatch, repository_class):
    opened = []
    closed = []
    real_connect = sqlite3.connect

    class TrackedConnection(sqlite3.Connection):
        def close(self):
            closed.append(self)
            return super().close()

    def connect(*args, **kwargs):
        connection = real_connect(*args, **kwargs, factory=TrackedConnection)
        opened.append(connection)
        return connection

    monkeypatch.setattr(sqlite3, "connect", connect)
    repository = repository_class(tmp_path / "synthetic.db")
    for _ in range(20):
        if isinstance(repository, PlaylistRepository):
            repository.list_summaries()
        else:
            repository.list_display_tracks()
    assert len(closed) == len(opened)
    with pytest.raises(sqlite3.OperationalError), repository._connect() as connection:
        connection.execute("INSERT INTO nonexistent VALUES (1)")
    assert len(closed) == len(opened)
    for connection in opened:
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            connection.execute("SELECT 1")
