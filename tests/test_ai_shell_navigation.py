"""Actual Qt shell routes for the approved assistant workflows."""

import pytest

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


def test_live_navigation_and_session_follow_current_engine_readiness(qapp, tmp_path):
    from tests.test_ai_narrator_controller import _readiness
    from tests.test_live_assistance import _set

    window = MainWindow(scan_service=EmptyScanner(), repository=TrackRepository(tmp_path / "tracks.db"))
    try:
        recommendation = _set()
        state = window._state.with_scanned_records(recommendation.ordered_tracks).model_copy(
            update={"last_recommendation": recommendation, "last_dj_readiness_report": _readiness()}
        )
        window._replace_app_state(state)
        window._sync_state()
        assert window.workflow_tabs.isTabEnabled(6)
        window.workflow_sidebar.setCurrentRow(6)
        assert window._state.current_screen == "live"
        live = window._live_assistant_screen
        assert live._current_track.path == "/a"
        live.load_next("/c")
        window._sync_state()
        assert live._current_track.path == "/c"
        assert live._history_table.rowCount() == 1
        window._replace_app_state(window._state.model_copy(update={"excluded_paths": frozenset({"/b"})}))
        window._sync_state()
        assert not window.workflow_tabs.isTabEnabled(6)
        assert live._current_track is None
        assert live._candidates == []
    finally:
        window.close()


def test_shell_sync_invalidates_inflight_narrator_when_set_changes(qapp, tmp_path, monkeypatch):
    from tests.test_ai_narrator_controller import _readiness
    from tests.test_live_assistance import _set

    window = MainWindow(scan_service=EmptyScanner(), repository=TrackRepository(tmp_path / "tracks.db"))
    try:
        first = _set()
        window._replace_app_state(
            window._state.model_copy(update={"last_recommendation": first, "last_dj_readiness_report": _readiness()})
        )
        window._sync_state()
        window.workflow_sidebar.setCurrentRow(2)
        starts = []
        monkeypatch.setattr(
            window._ai_narrator, "_start_worker", lambda operation, request_id: starts.append(request_id)
        )
        window._review_screen.ai_narrate_button.click()
        assert window._state.is_narrating and len(starts) == 1
        window._replace_app_state(window._state.model_copy(update={"last_recommendation": _set()}))
        window._sync_state()
        assert not window._state.is_narrating
        window._ai_narrator._on_worker_finished("Old response", starts[0])
        qapp.processEvents()
        assert window._state.ai_narrative_text is None
        assert "Set changed" in window._review_screen.ai_narrate_status.text()
    finally:
        window.close()


@pytest.mark.parametrize("screen_index", [1, 2])
def test_configure_ai_opens_real_settings_without_enabling(qapp, tmp_path, monkeypatch, screen_index):
    from PySide6.QtCore import QTimer

    from tests.test_ai_narrator_controller import _readiness
    from tests.test_live_assistance import _set

    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "0")
    monkeypatch.setenv("HOME", str(tmp_path))
    window = MainWindow(scan_service=EmptyScanner(), repository=TrackRepository(tmp_path / "tracks.db"))
    seen = []
    try:
        window._replace_app_state(
            window._state.with_scanned_records(_set().ordered_tracks).model_copy(
                update={"last_recommendation": _set(), "last_dj_readiness_report": _readiness()}
            )
        )
        window._sync_state()
        window.workflow_sidebar.setCurrentRow(screen_index)

        def inspect_dialog():
            dialog = window._settings_dialog
            seen.append(dialog is not None)
            if dialog is not None:
                assert not dialog._ai_panel.enabled_checkbox.isChecked()
                assert "never audio" in dialog._ai_panel.privacy_label.text()
                dialog.reject()

        QTimer.singleShot(0, inspect_dialog)
        button = (
            window._build_screen.copilot_configure_button
            if screen_index == 1
            else window._review_screen.configure_ai_button
        )
        button.click()
        qapp.processEvents()
        assert seen == [True]
        assert not window.settings.ai.enabled
    finally:
        window.close()


def test_saved_playlist_keyboard_open_preview_apply_and_save(qapp, tmp_path):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    from tests.test_live_assistance import _set

    window = MainWindow(scan_service=EmptyScanner(), repository=TrackRepository(tmp_path / "tracks.db"))
    try:
        tracks = _set().ordered_tracks
        window._replace_app_state(window._state.with_scanned_records(tracks))
        playlist = window._playlist_repository.create("Synthetic draft", [track.path for track in tracks])
        window._playlist_coordinator.refresh_list()
        window._sync_state()
        window.show()
        qapp.processEvents()
        window.workflow_sidebar.setCurrentRow(4)
        listing = window._playlists_screen.list_widget
        listing.setCurrentRow(0)
        listing.setFocus()
        QTest.keyClick(listing, Qt.Key.Key_Return)
        qapp.processEvents()
        assert window._state.current_screen == "editor"
        editor = window._playlist_editor
        editor.edit_input.setText("shorten to 2 tracks")
        QTest.mouseClick(editor.preview_button, Qt.MouseButton.LeftButton)
        assert editor.confirm_button.isEnabled()
        assert window._playlist_repository.get_by_id(playlist.id).track_paths == [track.path for track in tracks]
        QTest.mouseClick(editor.confirm_button, Qt.MouseButton.LeftButton)
        assert editor.is_dirty and len(editor._track_paths) == 2
        assert len(window._playlist_repository.get_by_id(playlist.id).track_paths) == 3
        QTest.mouseClick(editor.save_button, Qt.MouseButton.LeftButton)
        assert not editor.is_dirty
        assert len(window._playlist_repository.get_by_id(playlist.id).track_paths) == 2
        QTest.mouseClick(editor.back_button, Qt.MouseButton.LeftButton)
        assert window._state.current_screen == "playlists"
    finally:
        window.close()


def test_create_candidate_routes_are_snapshotted_on_ui_thread(qapp, tmp_path):
    window = MainWindow(scan_service=EmptyScanner(), repository=TrackRepository(tmp_path / "tracks.db"))
    try:
        assert window._ai_copilot._candidate_routes_factory == window._prep_candidate_routes
    finally:
        window.close()


@pytest.mark.parametrize("discard", [False, True])
def test_window_close_protects_unsaved_editor_draft(qapp, tmp_path, monkeypatch, discard):
    from PySide6.QtWidgets import QMessageBox

    window = MainWindow(scan_service=EmptyScanner(), repository=TrackRepository(tmp_path / "tracks.db"))
    playlist = window._playlist_repository.create("Draft", ["/a", "/b"])
    window._playlist_editor.set_playlist(playlist)
    window._playlist_editor._on_remove_clicked(1)
    assert window._playlist_editor.is_dirty
    window.show()
    questions = []
    answer = QMessageBox.StandardButton.Discard if discard else QMessageBox.StandardButton.Cancel
    monkeypatch.setattr(QMessageBox, "question", lambda *args: questions.append(args) or answer)
    try:
        window.close()
        assert len(questions) == 1
        assert "unsaved" in questions[0][2].lower()
        assert bool(getattr(window, "_closing", False)) is discard
        assert window.isVisible() is not discard
        assert window._playlist_repository.get_by_id(playlist.id).track_paths == ["/a", "/b"]
    finally:
        window._playlist_editor.discard_draft()
        window.close()
