"""Tests for LibraryScreen rendering."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.library_view_model import LibraryViewModel
from xfinaudio.desktop.screens.library_screen import LibraryScreen


def test_library_screen_renders_scan_settings_review(qapp: QApplication) -> None:
    """The scan settings review label is updated when the screen renders."""
    screen = LibraryScreen()
    vm = LibraryViewModel()
    state = AppState(selected_folder=Path("/music"))

    screen.render(vm, state, lightweight=True)

    expected = vm.scan_settings_review_text(state)
    assert screen.scan_settings_label.text() == expected
    assert ".mp3" in screen.scan_settings_label.text()
    assert "TBPM" in screen.scan_settings_label.text()
