"""Tests for ExportScreen user-facing copy warnings."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from xfinaudio.desktop.screens.export_screen import ExportScreen


def test_export_screen_guidance_label_explains_direct_serato_safety(qapp: QApplication) -> None:
    """Direct crate export identifies its destination and backup/audio-copy boundaries."""
    screen = ExportScreen()
    text = screen.export_guidance_label.text()

    assert "preview the destination" in text.lower()
    assert "export directly to Serato" in text
    assert "Existing crates are backed up before replacement" in text
    assert "audio files are not copied" in text
