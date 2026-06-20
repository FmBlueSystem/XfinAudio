from __future__ import annotations

from typing import get_type_hints

from xfinaudio.config.ports import SettingsRepositoryPort
from xfinaudio.config.settings import AppSettings
from xfinaudio.config.settings_repository import SettingsRepository


def test_settings_repository_port_is_desktop_free() -> None:
    hints = get_type_hints(SettingsRepositoryPort.load)

    assert hints["return"] is AppSettings
    assert "xfinaudio.desktop" not in SettingsRepositoryPort.__module__


def test_settings_repository_satisfies_settings_port(tmp_path) -> None:
    repo: SettingsRepositoryPort = SettingsRepository(tmp_path / "settings.json")

    repo.save(AppSettings())

    assert isinstance(repo.load(), AppSettings)
