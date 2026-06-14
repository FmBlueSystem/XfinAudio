"""Settings controller for XfinAudio — handles settings dialog open/apply."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from xfinaudio.config.settings import AppSettings
from xfinaudio.desktop.settings_dialog import SettingsDialog

if TYPE_CHECKING:
    from xfinaudio.desktop.main_window import SettingsPersistence


class SettingsHost(Protocol):
    """Structural host boundary for ``SettingsController``.

    Declares only the ``MainWindow`` members the controller accesses,
    decoupling settings logic from the concrete window type.
    """

    settings: AppSettings
    settings_repository: SettingsPersistence | None
    _export_screen: Any

    def _apply_settings(self, new_settings: AppSettings) -> None: ...
    def _format_safe_export_folder_label(self) -> str: ...
    def _sync_state(self) -> None: ...
    def tr(self, text: str) -> str: ...


class SettingsController:
    """Controller for opening and applying settings changes.

    Host (MainWindow) provides: settings, settings_repository, safe_export_folder_label,
    _format_safe_export_folder_label(), _sync_state(), tr()
    """

    def __init__(self, host: SettingsHost) -> None:
        self._host = host

    def open_dialog(self) -> None:
        """Open the settings dialog and apply changes if confirmed."""
        dialog = SettingsDialog(self._host.settings, parent=self._host)
        dialog.settings_changed.connect(self._host._apply_settings)
        dialog.exec()

    def apply(self, new_settings: AppSettings) -> None:
        """Apply and persist settings from the settings dialog."""
        old_lang = self._host.settings.ui.language
        self._host.settings = new_settings
        if self._host.settings_repository is not None:
            self._host.settings_repository.save(new_settings)
        self._host._export_screen.safe_export_folder_label.setText(self._host._format_safe_export_folder_label())
        self._host._sync_state()
        if new_settings.ui.language != old_lang:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.information(
                self._host,
                self._host.tr("Language Changed"),
                self._host.tr("Please restart XfinAudio for the language change to take effect."),
            )
