"""Injected interpretation still uses visible filters and the local edit boundary."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtWidgets import QWidget

from tests.test_optional_ai_controller import drain
from xfinaudio.ai.structured_assists import EditorInterpretation
from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.library_query import LibraryQuery
from xfinaudio.desktop.library_query_panel import LibraryQueryPanel
from xfinaudio.desktop.optional_ai_surfaces import install_library_editor_controls
from xfinaudio.desktop.playlist_coordinator import PlaylistCoordinator
from xfinaudio.desktop.screens.my_playlists_screen import MyPlaylistsScreen
from xfinaudio.desktop.screens.playlist_editor import PlaylistEditor
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_repository import PlaylistRepository


def host(qapp, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "1")
    window = QWidget()
    window._state = AppState()
    window.scanned_records = [
        TrackRecord(path="a", genre="House", bpm=120, camelot_key="8A", energy_level=4, metadata_status="complete"),
        TrackRecord(path="b", bpm=121, camelot_key="8A", energy_level=5, metadata_status="complete"),
        TrackRecord(path="c", bpm=122, camelot_key="8A", energy_level=6, metadata_status="complete"),
    ]
    window._library_screen = SimpleNamespace(query_panel=LibraryQueryPanel(lambda: ["House"]))
    window._playlist_editor = PlaylistEditor()
    window._playlist_repository = PlaylistRepository(tmp_path / "sets.db")
    window._playlists_screen = MyPlaylistsScreen()
    window._settings_controller = MagicMock()
    window._playlist_coordinator = PlaylistCoordinator(window)  # type: ignore[arg-type]
    return window


def test_library_ai_only_prepares_editable_filters_until_apply(qapp, tmp_path, monkeypatch):
    window = host(qapp, tmp_path, monkeypatch)
    services = SimpleNamespace(interpret_library_query=MagicMock(return_value=LibraryQuery(genre="House", bpm_min=120)))
    controls = install_library_editor_controls(window, services=services)
    controller = controls["library"]
    query = window._library_screen.query_panel
    query.request_input.setText("music that fits a relaxed early house set")
    controller.panel.consent.setChecked(True)
    controller.panel.ask_button.click()
    drain(qapp, controller)
    services.interpret_library_query.assert_called_once_with(query.request_input.text(), ["House"])
    assert query.fields["genre"].text() == "House"
    assert query.query.genre is None
    query.apply_button.click()
    assert query.query.genre == "House"
    controller.panel.configure_button.click()
    window._settings_controller.open_ai_settings_dialog.assert_called_once()


def test_editor_ai_previews_but_does_not_apply_or_save(qapp, tmp_path, monkeypatch):
    window = host(qapp, tmp_path, monkeypatch)
    saved = window._playlist_repository.create("Private Name", ["a", "b", "c"])
    window._playlist_editor.set_playlist(saved)
    services = SimpleNamespace(
        interpret_editor_request=MagicMock(return_value=EditorInterpretation(operation="shorten_tracks", target=2))
    )
    controller = install_library_editor_controls(window, services=services)["editor"]
    editor = window._playlist_editor
    editor.edit_input.setText("make this a very short opener")
    controller.panel.consent.setChecked(True)
    controller.panel.ask_button.click()
    drain(qapp, controller)
    services.interpret_editor_request.assert_called_once_with(editor.edit_input.text())
    assert editor._preview == ("a", "b")
    assert editor._track_paths == ["a", "b", "c"]
    assert window._playlist_repository.get_by_id(saved.id) == saved
    assert editor.confirm_button.isEnabled()
    assert "shorten to 2 tracks" in editor.status_label.text()


def test_missing_context_does_not_start_ai(qapp, tmp_path, monkeypatch):
    window = host(qapp, tmp_path, monkeypatch)
    window.scanned_records = []
    services = SimpleNamespace(interpret_library_query=MagicMock(), interpret_editor_request=MagicMock())
    controls = install_library_editor_controls(window, services=services)
    for controller in controls.values():
        controller.request.setText("help")
        controller.panel.consent.setChecked(True)
        controller.panel.ask_button.click()
        assert not controller.busy
    services.interpret_library_query.assert_not_called()
    services.interpret_editor_request.assert_not_called()


def test_editor_context_change_clears_ai_preview_but_local_preview_survives(qapp, tmp_path, monkeypatch):
    window = host(qapp, tmp_path, monkeypatch)
    saved = window._playlist_repository.create("Set", ["a", "b", "c"])
    editor = window._playlist_editor
    editor.set_playlist(saved)
    services = SimpleNamespace(
        interpret_editor_request=MagicMock(return_value=EditorInterpretation(operation="shorten_tracks", target=2))
    )
    controller = install_library_editor_controls(window, services=services)["editor"]
    controller.request.setText("shorten to 2 tracks")
    controller.panel.consent.setChecked(True)
    controller.panel.ask_button.click()
    drain(qapp, controller)
    assert editor._preview is not None
    window.scanned_records = list(window.scanned_records)
    controller.invalidate_if_context_changed()
    assert editor._preview is None
    controller.panel.ask_button.click()
    drain(qapp, controller)
    editor.preview_requested.connect(window._playlist_coordinator.preview_edit)
    editor.preview_button.click()
    assert editor._preview == ("a", "b")
