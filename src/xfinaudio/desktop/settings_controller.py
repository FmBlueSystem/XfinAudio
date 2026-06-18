"""Settings dialog controller."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QMessageBox, QWidget

from xfinaudio.config.settings import AppSettings
from xfinaudio.desktop.app_state import SettingsPersistence
from xfinaudio.desktop.screens import ExportScreen
from xfinaudio.desktop.settings_dialog import SettingsDialog


class SettingsController:
    def __init__(
        self,
        *,
        settings_getter: Callable[[], AppSettings],
        settings_setter: Callable[[AppSettings], None],
        settings_repository: SettingsPersistence | None,
        export_screen: ExportScreen,
        sync_state: Callable[[], None],
        tr: Callable[[str], str],
        message_parent: QWidget,
        dialog_setter: Callable[[SettingsDialog], None],
    ) -> None:
        self._settings_getter = settings_getter
        self._settings_setter = settings_setter
        self._settings_repository = settings_repository
        self._export_screen = export_screen
        self._sync_state = sync_state
        self._tr = tr
        self._message_parent = message_parent
        self._dialog_setter = dialog_setter
        self._settings_dialog: SettingsDialog | None = None

    def open_settings_dialog(self) -> None:
        self._settings_dialog = SettingsDialog(self._settings_getter(), parent=self._message_parent)
        self._dialog_setter(self._settings_dialog)
        self._settings_dialog.settings_changed.connect(self.apply_settings)
        self._settings_dialog.open_dialog()

    def on_spectral_cohesion_changed(self, value: int) -> None:
        settings = self._settings_getter()
        settings = settings.model_copy(
            update={"scoring": settings.scoring.model_copy(update={"spectral_cohesion": value / 100.0})}
        )
        self._settings_setter(settings)
        if self._settings_repository is not None:
            self._settings_repository.save(settings)
        self._sync_state()

    def apply_settings(self, new_settings: AppSettings) -> None:
        old_lang = self._settings_getter().ui.language
        self._settings_setter(new_settings)
        if self._settings_repository is not None:
            self._settings_repository.save(new_settings)
        self._export_screen.safe_export_folder_label.setText(self.format_safe_export_folder_label())
        self._sync_state()
        if new_settings.ui.language != old_lang:
            QMessageBox.information(
                self._message_parent,
                self._tr("Language Changed"),
                self._tr("Please restart XfinAudio for the language change to take effect."),
            )

    def format_safe_export_folder_label(self) -> str:
        folder = self._settings_getter().export.safe_export_folder
        if folder is None:
            return self._tr("No safe export folder selected")
        return self._tr("Safe export folder: {0}").format(folder)
