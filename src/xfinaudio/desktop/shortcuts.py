"""Keyboard shortcut bindings for MainWindow."""

from __future__ import annotations

from typing import Any

from PySide6.QtGui import QKeySequence, QShortcut


def bind_main_window_shortcuts(window: Any) -> dict[str, QShortcut]:
    shortcuts = [
        ("open_folder", QKeySequence.StandardKey.Open, window.choose_folder),
        ("focus_search", QKeySequence("Ctrl+F"), window._library_screen.search_input.setFocus),
        ("scan_metadata", QKeySequence("Ctrl+Shift+S"), window.scan_selected_folder),
        ("recommend_playlist", QKeySequence("Ctrl+R"), window._build_screen.recommend_button.click),
        ("export_recommendation", QKeySequence("Ctrl+E"), window._export_screen.export_button.click),
        ("toggle_missing_column", QKeySequence("Ctrl+M"), window._library_screen.missing_column_button.click),
        ("open_selected_track", QKeySequence("Return"), window._library_controller.open_selected_library_track),
        ("remove_selected_track", QKeySequence("Del"), window._library_controller.remove_selected_review_track),
        ("cancel_scan", QKeySequence("Esc"), window.cancel_scan),
        ("undo", QKeySequence("Ctrl+Z"), window._undo_toolbar.undo),
        ("redo", QKeySequence("Ctrl+Shift+Z"), window._undo_toolbar.redo),
    ]
    keyboard_shortcuts: dict[str, QShortcut] = {}
    for name, sequence, slot in shortcuts:
        shortcut = QShortcut(sequence, window)
        shortcut.activated.connect(slot)
        keyboard_shortcuts[name] = shortcut
    return keyboard_shortcuts
