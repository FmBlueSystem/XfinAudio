"""Menu bar construction and About dialog for the XfinAudio desktop window."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMessageBox

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMenuBar, QWidget


class MenuHost(Protocol):
    """Host boundary the MenuBuilder needs to wire menu actions."""

    def tr(self, text: str) -> str: ...
    def close(self) -> bool: ...
    def _open_settings_dialog(self) -> None: ...


class MenuBuilder:
    """Build the application menu bar and own the About dialog."""

    def __init__(self, host: MenuHost) -> None:
        self._host = host

    def build(self, menu_bar: QMenuBar) -> None:
        """Create the XfinAudio and Help menus on the provided menu bar."""
        host = self._host
        parent = host  # type: ignore[assignment]  # host is a QWidget at runtime
        app_menu = menu_bar.addMenu(host.tr("XfinAudio"))

        about_action = QAction(host.tr("About XfinAudio"), parent)
        about_action.triggered.connect(self.show_about_dialog)
        app_menu.addAction(about_action)

        app_menu.addSeparator()

        settings_action = QAction(host.tr("Settings…"), parent)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(host._open_settings_dialog)
        app_menu.addAction(settings_action)

        app_menu.addSeparator()

        quit_action = QAction(host.tr("Quit"), parent)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(host.close)
        app_menu.addAction(quit_action)

        help_menu = menu_bar.addMenu(host.tr("Help"))
        help_about_action = QAction(host.tr("About XfinAudio"), parent)
        help_about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(help_about_action)

    def show_about_dialog(self) -> None:
        """Show the About dialog with application metadata and trademark notices."""
        host = self._host
        parent: QWidget = host  # type: ignore[assignment]  # host is a QWidget at runtime
        QMessageBox.about(
            parent,
            host.tr("About XfinAudio"),
            "<h2 style='margin-bottom:2px;'>XfinAudio</h2>"
            "<p style='margin-top:0px; color:#8a9bb0; font-size:12px;'>" + host.tr("Version 1.0") + "</p>"
            "<p style='margin-top:12px;'>"
            + host.tr(
                "XfinAudio is a metadata-driven DJ playlist assistant that helps DJs "
                "build harmonically coherent playlists from existing track metadata."
            )
            + "</p>"
            "<p style='margin-top:8px; font-size:12px; color:#8a9bb0;'>"
            "© 2025 <b>BlueSystem.io</b> — "
            + host.tr("Audio Division")
            + ". "
            + host.tr("All rights reserved.")
            + "<br>"
            + host.tr("Developed by Freddy Molina.")
            + "</p>"
            "<p style='margin-top:8px; font-size:11px; color:#8a9bb0;'>"
            + host.tr("This software is open-source and distributed under the GNU General Public License v3.0.")
            + "</p>"
            "<hr>"
            "<p style='font-size:10px; color:#8a9bb0; line-height:1.4;'>"
            + host.tr(
                "Mixed In Key®, Camelot®, and Camelot System® are trademarks of Mixed In Key LLC. "
                "Serato™ and Serato DJ Pro™ are trademarks of Serato Limited. "
                "All other trademarks are property of their respective owners. "
                "XfinAudio is an independent project with no affiliation to these companies."
            )
            + "</p>",
        )
