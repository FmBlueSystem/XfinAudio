"""Modal settings dialog for XfinAudio export and library preferences."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.config.settings import AppSettings, ExportSettings


class SettingsDialog(QDialog):
    """Modal settings dialog for export and library preferences."""

    settings_changed = Signal(AppSettings)

    def __init__(self, settings: AppSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings.model_copy()
        self._pending_safe_export_folder: Path | None = settings.export.safe_export_folder
        self.setWindowTitle("Settings")
        self.setModal(True)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Export Settings group
        export_group = QGroupBox("Export Settings")
        export_layout = QHBoxLayout(export_group)
        export_layout.addWidget(QLabel("Safe export folder:"))
        self._safe_export_folder_label = QLabel(self._format_folder_label(self._pending_safe_export_folder))
        self._safe_export_folder_label.setMinimumWidth(220)
        export_layout.addWidget(self._safe_export_folder_label, 1)
        choose_button = QPushButton("Choose…")
        choose_button.clicked.connect(self._choose_safe_export_folder)
        export_layout.addWidget(choose_button)
        layout.addWidget(export_group)

        # Library Settings group (informational)
        library_group = QGroupBox("Library Settings")
        library_layout = QHBoxLayout(library_group)
        library_layout.addWidget(QLabel("Last scan folder:"))
        last_scan = self._settings.library.last_scan_folder
        self._last_scan_folder_label = QLabel(str(last_scan) if last_scan is not None else "None")
        self._last_scan_folder_label.setEnabled(False)
        library_layout.addWidget(self._last_scan_folder_label, 1)
        layout.addWidget(library_group)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _choose_safe_export_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose safe export folder")
        if folder:
            self._pending_safe_export_folder = Path(folder)
            self._safe_export_folder_label.setText(self._format_folder_label(self._pending_safe_export_folder))

    # ------------------------------------------------------------------
    # Dialog accept/reject
    # ------------------------------------------------------------------

    def accept(self) -> None:
        new_settings = self._settings.model_copy(
            update={"export": ExportSettings(safe_export_folder=self._pending_safe_export_folder)}
        )
        self.settings_changed.emit(new_settings)
        super().accept()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_folder_label(folder: Path | None) -> str:
        return str(folder) if folder is not None else "None"
