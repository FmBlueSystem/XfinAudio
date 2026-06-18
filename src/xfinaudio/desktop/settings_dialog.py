"""Modal settings dialog for XfinAudio export, library, and UI preferences."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.config.settings import AppSettings, ExportSettings, UiSettings


class SettingsDialog(QDialog):
    """Modal settings dialog for export, library, and UI preferences."""

    settings_changed = Signal(AppSettings)

    def __init__(self, settings: AppSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings.model_copy()
        self._pending_safe_export_folder: Path | None = settings.export.safe_export_folder
        self.setWindowTitle(self.tr("Settings"))
        self.setModal(True)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # UI Language group
        language_group = QGroupBox(self.tr("UI Language"))
        language_layout = QHBoxLayout(language_group)
        language_layout.addWidget(QLabel(self.tr("Language:")))
        self._language_combo = QComboBox()
        self._language_combo.addItem(self.tr("Auto (system default)"), "")
        self._language_combo.addItem("English", "en")
        self._language_combo.addItem("Español", "es")
        current_lang = self._settings.ui.language
        index = self._language_combo.findData(current_lang)
        if index >= 0:
            self._language_combo.setCurrentIndex(index)
        language_layout.addWidget(self._language_combo, 1)
        layout.addWidget(language_group)

        # Export Settings group
        export_group = QGroupBox(self.tr("Export Settings"))
        export_layout = QHBoxLayout(export_group)
        export_layout.addWidget(QLabel(self.tr("Safe export folder:")))
        self._safe_export_folder_label = QLabel(self._format_folder_label(self._pending_safe_export_folder))
        self._safe_export_folder_label.setMinimumWidth(220)
        export_layout.addWidget(self._safe_export_folder_label, 1)
        choose_button = QPushButton(self.tr("Choose…"))
        choose_button.clicked.connect(self._choose_safe_export_folder)
        export_layout.addWidget(choose_button)
        layout.addWidget(export_group)

        # Library Settings group (informational)
        library_group = QGroupBox(self.tr("Library Settings"))
        library_layout = QHBoxLayout(library_group)
        library_layout.addWidget(QLabel(self.tr("Last scan folder:")))
        last_scan = self._settings.library.last_scan_folder
        self._last_scan_folder_label = QLabel(str(last_scan) if last_scan is not None else self.tr("None"))
        self._last_scan_folder_label.setEnabled(False)
        library_layout.addWidget(self._last_scan_folder_label, 1)
        layout.addWidget(library_group)

        # Buttons
        button_layout = QHBoxLayout()
        self._reset_button = QPushButton(self.tr("Reset to Defaults"))
        self._reset_button.setObjectName("reset_to_defaults_button")
        self._reset_button.clicked.connect(self._reset_to_defaults)
        button_layout.addWidget(self._reset_button)
        button_layout.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        button_layout.addWidget(buttons)
        layout.addLayout(button_layout)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _choose_safe_export_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, self.tr("Choose safe export folder"))
        if folder:
            self._pending_safe_export_folder = Path(folder)
            self._safe_export_folder_label.setText(self._format_folder_label(self._pending_safe_export_folder))

    def _reset_to_defaults(self) -> None:
        """Ask for confirmation and reset all settings to release defaults."""
        reply = QMessageBox.question(
            self,
            self.tr("Reset Settings"),
            self.tr("Restore all settings to their default values?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.settings_changed.emit(AppSettings())
            super().accept()

    def open_dialog(self) -> None:
        """Open the modal dialog."""
        self.exec()

    def apply(self) -> None:
        """Apply the current dialog values."""
        self.accept()

    def reset_to_defaults(self) -> None:
        """Reset settings to release defaults."""
        self.settings_changed.emit(AppSettings())
        super().accept()

    # ------------------------------------------------------------------
    # Dialog accept/reject
    # ------------------------------------------------------------------

    def accept(self) -> None:
        selected_lang = self._language_combo.currentData()
        new_settings = self._settings.model_copy(
            update={
                "export": ExportSettings(safe_export_folder=self._pending_safe_export_folder),
                "ui": UiSettings(language=selected_lang),
            }
        )
        self.settings_changed.emit(new_settings)
        super().accept()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_folder_label(folder: Path | None) -> str:
        return str(folder) if folder is not None else "None"
