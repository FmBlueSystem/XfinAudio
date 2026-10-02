"""Saved-set assistant buttons use live repository evidence without writes."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from xfinaudio.desktop.playlist_coordinator import PlaylistCoordinator
from xfinaudio.desktop.screens.my_playlists_screen import MyPlaylistsScreen
from xfinaudio.desktop.screens.playlist_editor import PlaylistEditor
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_repository import PlaylistRepository


def test_search_and_compare_controls_are_grounded_and_read_only(qapp, tmp_path):
    repository = PlaylistRepository(tmp_path / "sets.db")
    first = repository.create("Sunset", ["a", "b"])
    second = repository.create("Peak", ["b", "c"])
    assert first.id is not None and second.id is not None
    screen = MyPlaylistsScreen()
    host = SimpleNamespace(
        _playlist_repository=repository,
        _playlists_screen=screen,
        _playlist_editor=PlaylistEditor(),
        _review_screen=MagicMock(),
        workflow_tabs=MagicMock(),
        scanned_records=[TrackRecord(path="a", genre="House", energy_level=3)],
    )
    coordinator = PlaylistCoordinator(host)  # type: ignore[arg-type]
    coordinator.connect_signals()
    coordinator.refresh_list()
    screen.query_input.setText("find playlists with house")
    screen.find_button.click()
    assert screen.list_widget.count() == 1
    assert "Sunset" in screen.assistant_output.toPlainText()
    assert "1/2 known" in screen.assistant_output.toPlainText()
    screen.query_input.setText("compare Sunset and Peak")
    screen.find_button.click()
    assert "1 shared unique track" in screen.assistant_output.toPlainText()
    assert screen.list_widget.count() == 2
    for i in range(2):
        screen.list_widget.item(i).setSelected(True)
    screen.compare_button.click()
    assert "Peak" in screen.assistant_output.toPlainText()
    assert repository.get_by_id(first.id) == first
    assert repository.get_by_id(second.id) == second
    repository.delete(second.id)
    screen.compare_button.click()
    assert "two" in screen.assistant_output.toPlainText()


def test_query_error_and_empty_results_do_not_invent_sets(qapp, tmp_path):
    repository = PlaylistRepository(tmp_path / "sets.db")
    repository.create("Set", [])
    screen = MyPlaylistsScreen()
    host = SimpleNamespace(_playlist_repository=repository, _playlists_screen=screen, scanned_records=[])
    coordinator = PlaylistCoordinator(host)  # type: ignore[arg-type]
    coordinator.search_saved_playlists("compare Set and nonexistent")
    assert "not found" in screen.assistant_output.toPlainText()
    coordinator.search_saved_playlists("find techno playlists")
    assert screen.list_widget.count() == 0
    assert "No saved playlists match" in screen.assistant_output.toPlainText()
