"""Actual Qt shell routes for the approved assistant workflows."""

from xfinaudio.desktop.app_state import VALID_SCREENS, AppState
from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.desktop.navigation import Navigation
from xfinaudio.library.track_repository import TrackRepository


class EmptyScanner:
    def scan(self, folder, **kwargs):
        return []


def test_editor_navigation_requires_loaded_playlist_and_idle_state():
    nav = Navigation()
    assert "editor" in VALID_SCREENS
    assert not nav.can_go_to("editor", AppState())
    loaded = AppState(editor_playlist_id=4)
    assert nav.can_go_to("editor", loaded)
    assert not nav.can_go_to("editor", loaded.model_copy(update={"is_scanning": True}))
    assert not nav.can_go_to("editor", loaded.model_copy(update={"is_recommending": True}))
    assert nav.back_screen(loaded.with_screen("editor")) == "playlists"


def test_editor_is_reachable_in_main_window_and_state_remains_immutable(qapp, tmp_path):
    window = MainWindow(scan_service=EmptyScanner(), repository=TrackRepository(tmp_path / "tracks.db"))
    try:
        assert window.workflow_tabs.count() == 8
        assert window.workflow_tabs.widget(7) is window._playlist_editor
        assert not window.workflow_tabs.isTabEnabled(7)
        playlist = window._playlist_repository.create("Synthetic", ["/synthetic/a.mp3"])
        window._playlist_editor.set_playlist(playlist)
        before = window._state
        window._show_playlist_editor()
        assert window.workflow_tabs.currentIndex() == 7
        assert window.workflow_sidebar.currentRow() == 7
        assert window._state.current_screen == "editor"
        assert before.current_screen == "library"
        window.workflow_sidebar.setCurrentRow(4)
        assert window._state.current_screen == "playlists"
        window._playlist_editor._playlist_id = None
        window._sync_state()
        assert window._state.editor_playlist_id is None
        assert not window.workflow_tabs.isTabEnabled(7)
    finally:
        window.close()


def test_unavailable_optional_screens_explain_next_step(qapp, tmp_path):
    window = MainWindow(scan_service=EmptyScanner(), repository=TrackRepository(tmp_path / "tracks.db"))
    try:
        assert "ready" in window.workflow_sidebar.item(6).toolTip().lower()
        assert "saved playlist" in window.workflow_sidebar.item(7).toolTip().lower()
    finally:
        window.close()
