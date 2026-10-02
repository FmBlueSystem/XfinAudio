"""Isolated preferences never activate loudness/provider work or expose paths."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from xfinaudio.config.settings import AppSettings
from xfinaudio.config.settings_repository import SettingsRepository
from xfinaudio.headless.backend import BackendError, HeadlessBackend


def test_preferences_defaults_reuse_volume_and_do_not_activate_legacy_write_defaults(tmp_path):
    backend = HeadlessBackend(tmp_path / "data")
    snapshot = backend.execute("settings.get", {})
    assert snapshot["previewVolume"] == AppSettings().audio.preview_volume == 0.7
    assert snapshot["watchLibrary"] is True
    assert len(snapshot["revision"]) == 64
    assert snapshot["capabilities"] == {"loudnessWriteback": True, "providers": True, "language": "es"}
    assert snapshot["libraryLabels"] == [] and snapshot["recoveryWarning"] is False
    assert not (tmp_path / "data" / "settings.json").exists()


def test_preferences_save_restart_and_preserve_unrelated_settings_without_secret_paths(tmp_path):
    data = tmp_path / "data"
    settings = AppSettings().model_copy(
        update={
            "ai": AppSettings().ai.model_copy(update={"enabled": True, "env_file": Path("/private/do-not-read.env")}),
            "loudness": AppSettings().loudness.model_copy(update={"enabled": True, "target_lufs": -18}),
        }
    )
    SettingsRepository(data / "settings.json").save(settings)
    backend = HeadlessBackend(data)
    before = backend.execute("settings.get", {})
    assert "private" not in json.dumps(before) and "env_file" not in json.dumps(before)
    result = backend.execute(
        "settings.update", {"revision": before["revision"], "previewVolume": 0.25, "watchLibrary": False}
    )
    assert (
        result["previewVolume"] == 0.25 and result["watchLibrary"] is False and result["revision"] != before["revision"]
    )
    persisted = SettingsRepository(data / "settings.json").load()
    assert persisted.ai == settings.ai and persisted.loudness == settings.loudness
    assert persisted.library.watch_for_changes is False
    restored = HeadlessBackend(data).execute("settings.get", {})
    assert restored == result


def test_stale_revision_does_not_overwrite_external_preferences(tmp_path):
    data = tmp_path / "data"
    backend = HeadlessBackend(data)
    first = backend.execute("settings.get", {})
    external = AppSettings().model_copy(
        update={"audio": AppSettings().audio.model_copy(update={"preview_volume": 0.2})}
    )
    repository = SettingsRepository(data / "settings.json")
    repository.save(external)
    with pytest.raises(BackendError) as failure:
        backend.execute("settings.update", {"revision": first["revision"], "previewVolume": 0.9, "watchLibrary": False})
    assert failure.value.code == "stale_settings"
    assert repository.load() == external
    assert backend.execute("settings.get", {})["previewVolume"] == 0.2


@pytest.mark.parametrize("contents", [b"broken json", b'{"settings_version":999}', b"[]"])
def test_corrupt_settings_are_preserved_and_recovery_stays_visible_without_path_leak(tmp_path, contents):
    backend = HeadlessBackend(tmp_path / "data")
    path = tmp_path / "data" / "settings.json"
    path.write_bytes(contents)
    first = backend.execute("settings.get", {})
    assert first["recoveryWarning"] is True and first["previewVolume"] == 0.7
    backups = list(path.parent.glob("settings.json.recovery-*"))
    assert len(backups) == 1 and backups[0].read_bytes() == contents
    assert str(path.parent) not in json.dumps(first)
    assert backend.execute("settings.get", {}) == first
    backend.execute("settings.update", {"revision": first["revision"], "previewVolume": 0.5, "watchLibrary": True})
    assert SettingsRepository(path).load().loudness.enabled is False
    assert backups[0].read_bytes() == contents


@pytest.mark.parametrize(
    "patch",
    [
        {"previewVolume": -0.1},
        {"previewVolume": 1.1},
        {"previewVolume": float("nan")},
        {"previewVolume": 10**400},
        {"previewVolume": float("inf")},
        {"previewVolume": True},
        {"watchLibrary": 1},
        {"revision": str(uuid4())},
        {"path": "/private"},
        {"ai": {"enabled": True}},
    ],
)
def test_bad_preferences_are_rejected_without_creating_settings(tmp_path, patch):
    backend = HeadlessBackend(tmp_path / "data")
    snapshot = backend.execute("settings.get", {})
    with pytest.raises(BackendError):
        backend.execute(
            "settings.update", {"revision": snapshot["revision"], "previewVolume": 0.7, "watchLibrary": True, **patch}
        )
    assert not (tmp_path / "data" / "settings.json").exists()


@pytest.mark.parametrize("entry", ["settings.json", ".settings.lock"])
def test_settings_or_lock_symlinks_cannot_read_or_write_external_file(tmp_path, entry):
    backend = HeadlessBackend(tmp_path / "data")
    victim = tmp_path / "external.json"
    victim.write_text('{"audio":{"preview_volume":0.01}}')
    before = victim.read_bytes()
    (tmp_path / "data" / entry).symlink_to(victim)
    with pytest.raises(BackendError) as failure:
        backend.execute("settings.get", {})
    assert failure.value.code == "settings_unavailable"
    assert victim.read_bytes() == before


def test_oversized_settings_fail_closed_without_recovery_or_allocation(tmp_path):
    backend = HeadlessBackend(tmp_path / "data")
    path = tmp_path / "data" / "settings.json"
    with path.open("wb") as handle:
        handle.truncate(256 * 1024 + 1)
    with pytest.raises(BackendError):
        backend.execute("settings.get", {})
    assert path.stat().st_size == 256 * 1024 + 1
    assert not list(path.parent.glob("*.recovery-*"))
