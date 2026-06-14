"""Tests for ExportScreen user-facing copy warnings."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from xfinaudio.desktop.screens.export_screen import ExportScreen


def test_export_screen_guidance_label_warns_about_live_serato_writes(qapp: QApplication) -> None:
    """The default export guidance label warns that live Serato writes are not part of the RC."""
    screen = ExportScreen()
    text = screen.export_guidance_label.text()

    assert "live serato" in text.lower()
    assert "not part of the verified release candidate" in text
    assert "back up" in text.lower()
