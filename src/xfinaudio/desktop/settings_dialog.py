"""Modal settings dialog for XfinAudio export, library, and UI preferences."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.config.settings import AppSettings, ExportSettings, UiSettings
from xfinaudio.genre.settings import (
    DEFAULT_LLM_TIEBREAKER_MODEL,
    DEFAULT_LLM_TIEBREAKER_URL,
    GenreEnrichmentSettings,
)


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

        # Genre Enrichment group
        layout.addWidget(self._build_genre_enrichment_group(self._settings.genre_enrichment))

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

    # ------------------------------------------------------------------
    # Dialog accept/reject
    # ------------------------------------------------------------------

    def accept(self) -> None:
        selected_lang = self._language_combo.currentData()
        new_settings = self._settings.model_copy(
            update={
                "export": ExportSettings(safe_export_folder=self._pending_safe_export_folder),
                "ui": UiSettings(language=selected_lang),
                "genre_enrichment": self._current_genre_settings(),
            }
        )
        self.settings_changed.emit(new_settings)
        super().accept()

    # ------------------------------------------------------------------
    # Genre enrichment helpers
    # ------------------------------------------------------------------

    # Provider keys that the dialog exposes, in display order.
    _PROVIDER_KEYS: tuple[str, ...] = ("lastfm", "spotify", "deezer")
    _PROVIDER_LABELS: dict[str, str] = {
        "lastfm": "Last.fm",
        "spotify": "Spotify",
        "deezer": "Deezer",
    }

    def _build_genre_enrichment_group(self, settings: GenreEnrichmentSettings) -> QGroupBox:
        """Build the 'Genre Enrichment' group: enable, per-provider toggles + keys, LLM block."""
        group = QGroupBox(self.tr("Genre Enrichment"))
        outer = QVBoxLayout(group)

        intro = QLabel(
            self.tr(
                "Optional: enrich each track's genre with consensus from third-party providers. "
                "All providers are off by default. Last.fm, Spotify, and Deezer require your own "
                "API key and store data only in your local cache."
            )
        )
        intro.setWordWrap(True)
        outer.addWidget(intro)

        # Master enable
        self._genre_enabled = QCheckBox(self.tr("Enable genre enrichment"))
        self._genre_enabled.setChecked(settings.enabled)
        outer.addWidget(self._genre_enabled)

        # Per-provider rows
        self._provider_toggles: dict[str, QCheckBox] = {}
        self._api_key_fields: dict[str, QLineEdit] = {}
        providers_group = QGroupBox(self.tr("Providers"))
        providers_layout = QFormLayout(providers_group)
        for key in self._PROVIDER_KEYS:
            label_text = self._PROVIDER_LABELS[key]
            toggle = QCheckBox(self.tr(f"Enable {label_text}"))
            toggle.setChecked(bool(settings.providers.get(key, False)))
            api_field = QLineEdit()
            api_field.setEchoMode(QLineEdit.EchoMode.Password)
            api_field.setPlaceholderText(self.tr("API key (required by this provider)"))
            api_field.setText(settings.api_keys.get(key, ""))
            providers_layout.addRow(toggle, api_field)
            self._provider_toggles[key] = toggle
            self._api_key_fields[key] = api_field
        outer.addWidget(providers_group)

        # LLM tie-breaker block
        llm_group = QGroupBox(self.tr("Local LLM tie-breaker (opt-in)"))
        llm_layout = QFormLayout(llm_group)
        self._llm_enabled = QCheckBox(self.tr("Enable local LLM tie-breaker"))
        self._llm_enabled.setChecked(settings.llm_tiebreaker_enabled)
        self._llm_url = QLineEdit(settings.llm_tiebreaker_url or DEFAULT_LLM_TIEBREAKER_URL)
        self._llm_model = QLineEdit(settings.llm_tiebreaker_model or DEFAULT_LLM_TIEBREAKER_MODEL)
        llm_layout.addRow(self._llm_enabled)
        llm_layout.addRow(self.tr("Local endpoint URL:"), self._llm_url)
        llm_layout.addRow(self.tr("Model name:"), self._llm_model)
        llm_warning = QLabel(
            self.tr(
                "Default: local Ollama at http://localhost:11434. The LLM is restricted to picking "
                "from the already-normalized top candidates. It never invents genres and never "
                "contacts a cloud endpoint."
            )
        )
        llm_warning.setWordWrap(True)
        llm_layout.addRow(llm_warning)
        outer.addWidget(llm_group)

        return group

    def _current_genre_settings(self) -> GenreEnrichmentSettings:
        """Read the current widget state into a GenreEnrichmentSettings."""
        providers: dict[str, bool] = {}
        api_keys: dict[str, str] = {}
        for key in self._PROVIDER_KEYS:
            providers[key] = self._provider_toggles[key].isChecked()
            api_keys[key] = self._api_key_fields[key].text()
        return GenreEnrichmentSettings(
            enabled=cast(QCheckBox, self._genre_enabled).isChecked(),
            providers=providers,
            api_keys=api_keys,
            llm_tiebreaker_enabled=cast(QCheckBox, self._llm_enabled).isChecked(),
            llm_tiebreaker_url=cast(QLineEdit, self._llm_url).text() or DEFAULT_LLM_TIEBREAKER_URL,
            llm_tiebreaker_model=cast(QLineEdit, self._llm_model).text() or DEFAULT_LLM_TIEBREAKER_MODEL,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_folder_label(folder: Path | None) -> str:
        return str(folder) if folder is not None else "None"
