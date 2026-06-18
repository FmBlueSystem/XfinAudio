"""Tests for settings application from MainWindow."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from xfinaudio.config.settings import AppSettings, ExportSettings
from xfinaudio.desktop.main_window import MainWindow, SettingsPersistence


class _FakeRepository(SettingsPersistence):
    def __init__(self) -> None:
        self.saved: list[AppSettings] = []

    def save(self, settings: AppSettings) -> None:
        self.saved.append(settings)


class _MockHost:
    def __init__(self) -> None:
        self.settings = AppSettings(
            export=ExportSettings(safe_export_folder=Path("/custom/export")),
        )
        self.settings_repository: SettingsPersistence | None = _FakeRepository()
        self._export_screen = MagicMock()
        self.synced = False

    def _apply_settings(self, new_settings: AppSettings) -> None:
        self.settings = new_settings

    def _format_safe_export_folder_label(self) -> str:
        return str(self.settings.export.safe_export_folder)

    def _sync_state(self) -> None:
        self.synced = True

    def tr(self, text: str) -> str:
        return text


@pytest.fixture
def host() -> _MockHost:
    return _MockHost()


def test_reset_to_defaults_applies_default_settings(host: _MockHost) -> None:
    """reset_to_defaults applies AppSettings defaults and persists them."""
    MainWindow._apply_settings(host, AppSettings())  # type: ignore[arg-type]

    assert host.settings == AppSettings()
    assert host.settings.export.safe_export_folder is None
    assert host.synced is True
    assert host.settings_repository.saved == [host.settings]


def test_apply_persists_custom_settings(host: _MockHost) -> None:
    """apply persists the provided settings."""
    new_settings = AppSettings(export=ExportSettings(safe_export_folder=Path("/another")))

    MainWindow._apply_settings(host, new_settings)  # type: ignore[arg-type]

    assert host.settings == new_settings
    assert host.settings_repository.saved[-1] == new_settings
