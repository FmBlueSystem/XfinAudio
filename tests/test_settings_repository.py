import json
from pathlib import Path

import pytest

from xfinaudio.config.settings import (
    AppSettings,
    BuildSessionSettings,
    ExportSettings,
    LibrarySettings,
    LoudnessSettings,
)
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


def test_settings_repository_save_then_load_preserves_last_scan_folder(tmp_path: Path) -> None:
    repository = SettingsRepository(tmp_path / "settings.json")
    library_folder = tmp_path / "library"
    settings = AppSettings(library=LibrarySettings(last_scan_folder=library_folder))

    repository.save(settings)
    loaded = repository.load()

    assert loaded.library.last_scan_folder == library_folder


def test_settings_repository_save_then_load_preserves_build_session(tmp_path: Path) -> None:
    repository = SettingsRepository(tmp_path / "settings.json")
    settings = AppSettings(
        build=BuildSessionSettings(
            excluded_paths=frozenset({"/music/one.flac"}),
            locked_paths=frozenset({"/music/two.flac"}),
            genre_focus="Techno",
        )
    )

    repository.save(settings)
    loaded = repository.load()

    assert loaded.build == settings.build


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


def test_settings_repository_loads_v1_payload_without_loudness_and_round_trips_defaults(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({"settings_version": 1, "audio": {"preview_volume": 0.3}}), encoding="utf-8")
    repository = SettingsRepository(settings_path)

    loaded = repository.load()
    repository.save(loaded)

    persisted = json.loads(settings_path.read_text(encoding="utf-8"))
    assert loaded.settings_version == 1
    assert loaded.loudness.enabled is True
    assert persisted["settings_version"] == 1
    assert persisted["loudness"] == {"enabled": True, "target_lufs": -10.0, "tolerance_lu": 2.0}


def test_settings_repository_round_trips_custom_loudness_analysis_policy(tmp_path: Path) -> None:
    repository = SettingsRepository(tmp_path / "settings.json")
    settings = AppSettings(loudness=LoudnessSettings(enabled=False, target_lufs=-14.0, tolerance_lu=1.5))

    repository.save(settings)

    assert repository.load().loudness == settings.loudness


@pytest.mark.parametrize("failure", ["fsync", "replace"])
def test_atomic_save_preserves_previous_settings_on_failure(tmp_path: Path, monkeypatch, failure: str) -> None:
    import os

    path = tmp_path / "settings.json"
    repository = SettingsRepository(path)
    previous = AppSettings(loudness=LoudnessSettings(enabled=False))
    repository.save(previous)
    original_bytes = path.read_bytes()

    def fail(*args, **kwargs):
        raise OSError("synthetic disk failure")

    monkeypatch.setattr(os, failure, fail)
    with pytest.raises(SettingsRepositoryError, match="Unable to write"):
        repository.save(AppSettings())
    assert path.read_bytes() == original_bytes
    assert repository.load() == previous
    assert sorted(p.name for p in tmp_path.iterdir()) == ["settings.json"]


@pytest.mark.parametrize("content", [b"{broken", b"[]", b'{"settings_version":999}', b"\xff"])
def test_load_with_recovery_preserves_invalid_bytes_and_reports_path(tmp_path: Path, content: bytes) -> None:
    path = tmp_path / "settings.json"
    path.write_bytes(content)
    repository = SettingsRepository(path)
    assert repository.load_with_recovery() == AppSettings()
    backups = list(tmp_path.glob("settings.json.recovery-*"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == content
    assert not path.exists()
    assert repository.recovery_warning is not None
    assert str(backups[0]) in repository.recovery_warning
    repository.save(AppSettings())
    assert backups[0].read_bytes() == content


def test_load_recovery_preservation_failure_leaves_original(tmp_path: Path, monkeypatch) -> None:
    import os

    path = tmp_path / "settings.json"
    path.write_bytes(b"{broken")
    repository = SettingsRepository(path)

    def fail(*args):
        raise OSError("synthetic read-only directory")

    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(SettingsRepositoryError, match="preserve"):
        repository.load_with_recovery()
    assert path.read_bytes() == b"{broken"
    assert list(tmp_path.iterdir()) == [path]
