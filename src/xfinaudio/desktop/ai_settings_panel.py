"""Explicit, credential-free controls for the optional AI provider."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.ai.connection_test import PROBE_MESSAGE, ConnectionStatus, configuration_status, endpoint_label
from xfinaudio.ai.nan_client import default_env_file_path
from xfinaudio.config.settings import AiSettings
from xfinaudio.desktop.ai_connection_probe import ConnectionProbe


class AiSettingsPanel(QGroupBox):
    def __init__(self, settings: AiSettings, parent: QWidget | None = None) -> None:
        super().__init__(self.tr("AI Settings"), parent)
        self.setObjectName("ai_settings_panel")
        self._env_file = settings.env_file
        self._probe = ConnectionProbe(self)
        self._probe.completed.connect(self._show_status)
        self._probe.busy_changed.connect(self._update_buttons)
        layout = QVBoxLayout(self)
        self.enabled_checkbox = QCheckBox(self.tr("Enable AI for actions I request"))
        self.enabled_checkbox.setObjectName("ai_enabled_checkbox")
        self.enabled_checkbox.setChecked(settings.enabled)
        layout.addWidget(self.enabled_checkbox)
        provider_row = QHBoxLayout()
        provider_row.addWidget(QLabel(self.tr("Provider:")))
        self.provider_combo = QComboBox()
        self.provider_combo.setObjectName("ai_provider_combo")
        self.provider_combo.addItem("Nan Builders", "nan")
        provider_row.addWidget(self.provider_combo, 1)
        layout.addLayout(provider_row)
        self.privacy_label = self._label(
            self.tr(
                "AI actions send your request text and track/set metadata (titles, artists, genres, BPM, key, energy "
                "and transition/readiness summaries) to {0}; never audio. "
                "Known and recognizable file paths are removed. Avoid private information in free text. "
                "Opening Settings sends nothing. Offline tools remain available."
            ).format(endpoint_label()),
            "ai_data_sharing_disclosure",
        )
        layout.addWidget(self.privacy_label)
        self.guidance_label = self._label(
            self.tr(
                "Configure NAN_API_KEY outside this app, in your launch environment or an operator-owned env file. "
                "Keep that file private (owner-only access). The environment key takes precedence. "
                "Never paste keys here; XfinAudio stores only the file path."
            ),
            "ai_secure_configuration_guidance",
        )
        layout.addWidget(self.guidance_label)
        self.file_label = self._label("", "ai_env_file_label")
        layout.addWidget(self.file_label)
        file_row = QHBoxLayout()
        self.choose_button = QPushButton(self.tr("Choose existing env file…"))
        self.choose_button.setObjectName("ai_choose_env_file_button")
        self.choose_button.clicked.connect(self._choose_file)
        self.default_button = QPushButton(self.tr("Use default file"))
        self.default_button.setObjectName("ai_default_env_file_button")
        self.default_button.clicked.connect(self._use_default_file)
        file_row.addWidget(self.choose_button)
        file_row.addWidget(self.default_button)
        file_row.addStretch()
        layout.addLayout(file_row)
        self.test_disclosure = self._label(
            self.tr(
                'Test connection sends only "{0}" plus the model name and app identifier to {1}, authenticated '
                "with your key. No library content is sent. It may use provider quota. "
                "Testing does not save or enable AI for other actions."
            ).format(PROBE_MESSAGE, endpoint_label()),
            "ai_test_disclosure",
        )
        layout.addWidget(self.test_disclosure)
        self.status_label = self._label("", "ai_status_label")
        layout.addWidget(self.status_label)
        test_row = QHBoxLayout()
        self.test_button = QPushButton(self.tr("Test connection"))
        self.test_button.setObjectName("ai_test_connection_button")
        self.test_button.clicked.connect(self._test_connection)
        self.cancel_button = QPushButton(self.tr("Cancel test"))
        self.cancel_button.setObjectName("ai_cancel_test_button")
        self.cancel_button.clicked.connect(self._cancel_test)
        test_row.addWidget(self.test_button)
        test_row.addWidget(self.cancel_button)
        test_row.addStretch()
        layout.addLayout(test_row)
        self.enabled_checkbox.toggled.connect(self._refresh_status)
        self._refresh_status()

    def settings(self) -> AiSettings:
        return AiSettings(enabled=self.enabled_checkbox.isChecked(), provider="nan", env_file=self._env_file)

    def cancel_pending(self) -> None:
        """Invalidate callbacks on dialog dismissal, save or configuration change."""
        self._probe.cancel()

    def _choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.tr("Choose existing AI env file"))
        if path:
            self._env_file = Path(path)
            self._refresh_status()

    def _use_default_file(self) -> None:
        self._env_file = None
        self._refresh_status()

    def _refresh_status(self) -> None:
        self.cancel_pending()
        self.file_label.setText(self.tr("Credential file: {0}").format(self._env_file or default_env_file_path()))
        self._show_status(configuration_status(self.settings()))

    def _show_status(self, status: ConnectionStatus) -> None:
        self.status_label.setText(self.tr(status.message))
        self._update_buttons()

    def _update_buttons(self) -> None:
        ready = configuration_status(self.settings()).state == "untested"
        self.test_button.setEnabled(ready and not self._probe.busy)
        self.cancel_button.setVisible(self._probe.busy)
        self.cancel_button.setEnabled(self._probe.busy)

    def _test_connection(self) -> None:
        if self._probe.busy:
            return
        status = configuration_status(self.settings())
        if status.state != "untested":
            self._show_status(status)
            return
        self.status_label.setText(self.tr("Testing connection…"))
        self._probe.start(self.settings())

    def _cancel_test(self) -> None:
        self.cancel_pending()
        self.status_label.setText(
            self.tr("Test cancelled. An already sent request may finish; retry when it stops. No settings were saved.")
        )
        self.cancel_button.setEnabled(False)

    @staticmethod
    def _label(text: str, name: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName(name)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        return label
