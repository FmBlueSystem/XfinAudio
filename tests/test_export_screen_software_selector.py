"""Tests for ExportScreen software selector."""

from PySide6.QtWidgets import QApplication

from xfinaudio.desktop.screens.export_screen import ExportScreen


def test_export_screen_has_software_selector(qapp: QApplication) -> None:
    screen = ExportScreen()
    assert screen.software_selector is not None


def test_export_screen_selector_has_expected_options(qapp: QApplication) -> None:
    screen = ExportScreen()
    options = [screen.software_selector.itemText(i) for i in range(screen.software_selector.count())]
    assert "Serato" in options
    assert "Rekordbox" in options
    assert "Traktor" in options
    assert "VirtualDJ" in options


def test_export_screen_software_changed_signal(qapp: QApplication) -> None:
    screen = ExportScreen()
    received: list[str] = []
    screen.software_changed.connect(lambda name: received.append(name))
    screen.software_selector.setCurrentText("Rekordbox")
    assert received == ["Rekordbox"]


def test_export_screen_button_text_updates_with_software(qapp: QApplication) -> None:
    screen = ExportScreen()
    screen.software_selector.setCurrentText("Rekordbox")
    assert "Rekordbox" in screen.export_button.text()
    screen.software_selector.setCurrentText("Traktor")
    assert "Traktor" in screen.export_button.text()
