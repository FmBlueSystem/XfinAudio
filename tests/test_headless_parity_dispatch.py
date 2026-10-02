"""Backend composition of independently tested local parity adapters."""

from xfinaudio.headless.backend import HeadlessBackend


def test_library_and_saved_browsers_are_allowlisted_and_composed(tmp_path):
    backend = HeadlessBackend(tmp_path)
    assert backend.execute("library.query", {})["tracks"] == []
    assert backend.execute("playlist.search", {})["playlists"] == []
    assert backend.execute("playlist.deleted.list", {}) == {"playlists": []}
