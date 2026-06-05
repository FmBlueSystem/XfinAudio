import json
from pathlib import Path

import pytest

from xfinaudio.config.settings import AppSettings, ExportSettings
from xfinaudio.config.settings_repository import SettingsRepository, SettingsRepositoryError


def test_settings_repository_missing_file_returns_default_settings(tmp_path: Path) -> None:
    repository = SettingsRepository(tmp_path / "settings.json")

    settings = repository.load()

    assert settings == AppSettings()


def test_settings_repository_save_then_load_preserves_safe_export_folder(tmp_path: Path) -> None:
    repository = SettingsRepository(tmp_path / "settings.json")
    export_folder = tmp_path / "safe-export"
    settings = AppSettings(export=ExportSettings(safe_export_folder=export_folder))

    repository.save(settings)
    loaded = repository.load()

    assert loaded.export.safe_export_folder == export_folder


def test_settings_repository_future_settings_version_raises_typed_error(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({"settings_version": 999}), encoding="utf-8")
    repository = SettingsRepository(settings_path)

    with pytest.raises(SettingsRepositoryError, match="Unsupported settings file"):
        repository.load()


def test_settings_repository_malformed_json_raises_typed_error(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{not-json", encoding="utf-8")
    repository = SettingsRepository(settings_path)

    with pytest.raises(SettingsRepositoryError, match="Malformed settings JSON"):
        repository.load()
