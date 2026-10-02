"""The real window receives five independent, default-off optional controls."""

from PySide6.QtWidgets import QPushButton

from tests.test_main_window_playlists import make_window


def test_installation_preserves_offline_controls_and_has_accessible_actions(qapp, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "0")
    window = make_window()
    offline = [
        window._library_screen.query_panel.interpret_button,
        window._playlist_editor.preview_button,
        window._playlists_screen.find_button,
        window._metadata_screen.repair_help_button,
    ]
    before = [button.isEnabled() for button in offline]
    controls = window._optional_ai_assists
    assert set(controls) == {"library", "editor", "saved", "metadata", "live"}
    for controller in controls.values():
        assert not controller.panel.consent.isChecked()
        for button in controller.panel.findChildren(QPushButton):
            assert button.toolTip() and button.accessibleName()
    assert [button.isEnabled() for button in offline] == before
    window.close()
