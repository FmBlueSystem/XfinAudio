"""Tests for the legacy MainWindow shell compatibility boundary."""

from __future__ import annotations

from xfinaudio.desktop import layout, shell_compat
from xfinaudio.desktop.main_window import MainWindow


def test_layout_no_longer_owns_legacy_method_installation() -> None:
    assert not hasattr(layout, "install_layout_methods")


def test_shell_compat_names_legacy_layout_methods() -> None:
    assert "choose_folder" in shell_compat.LEGACY_LAYOUT_METHODS
    assert "_apply_song_filter" in shell_compat.LEGACY_LAYOUT_METHODS
    assert "_refresh_idle_action_state" in shell_compat.LEGACY_LAYOUT_METHODS


def test_main_window_keeps_legacy_layout_methods_available() -> None:
    assert callable(MainWindow.choose_folder)
    assert callable(MainWindow._apply_song_filter)
    assert callable(MainWindow._refresh_idle_action_state)
