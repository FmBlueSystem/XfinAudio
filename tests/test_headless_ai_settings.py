"""Optional AI preferences never discover credentials or activate a provider."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from pydantic import ValidationError

from xfinaudio.config.settings import AiSettings, AppSettings
from xfinaudio.config.settings_repository import SettingsRepository
from xfinaudio.headless.common import BackendError
from xfinaudio.headless.preferences import SETTINGS_FIELDS, PreferencesService


def service(path: Path) -> PreferencesService:
    path.mkdir(parents=True, exist_ok=True)
    return PreferencesService(cast(Any, SimpleNamespace(data_dir=path, roots=[])))


def test_ai_default_is_unconfigured_and_does_not_write_or_enable_capability(tmp_path: Path) -> None:
    preferences = service(tmp_path)
    snapshot = preferences.get_ai()
    assert snapshot == {
        "revision": preferences.execute("settings.get", {})["revision"],
        "enabled": False,
        "provider": "nan",
        "credentialLabel": None,
        "configured": False,
    }
    assert preferences.ai_settings() == AiSettings()
    assert not (tmp_path / "settings.json").exists()
    assert {"settings.get": set(), "settings.update": {"revision", "previewVolume", "watchLibrary"}} == SETTINGS_FIELDS
    assert preferences.execute("settings.get", {})["capabilities"]["providers"] is True


def test_ai_toggles_and_private_path_selection_preserve_unrelated_settings(tmp_path: Path) -> None:
    preferences = service(tmp_path)
    original = AppSettings().model_copy(
        update={"audio": AppSettings().audio.model_copy(update={"preview_volume": 0.2})}
    )
    preferences.repository.save(original)
    before = preferences.get_ai()
    chosen = tmp_path / "absent" / "selected.env"
    selected = preferences.set_ai_credential({"revision": before["revision"], "path": chosen})
    assert selected["configured"] is True and selected["credentialLabel"] == "selected.env"
    assert selected["enabled"] is False
    enabled = preferences.update_ai({"revision": selected["revision"], "enabled": True})
    assert enabled["enabled"] is True and enabled["configured"] is True
    assert enabled["revision"] != selected["revision"]
    stored = preferences.ai_settings()
    assert stored == AiSettings(enabled=True, env_file=chosen)
    with pytest.raises(ValidationError):
        stored.enabled = False
    persisted = SettingsRepository(tmp_path / "settings.json").load()
    assert persisted.model_copy(update={"ai": original.ai}) == original
    assert service(tmp_path).get_ai() == enabled
    assert str(tmp_path) not in json.dumps(enabled)
    cleared = preferences.set_ai_credential({"revision": enabled["revision"], "path": None})
    assert cleared["enabled"] is True and cleared["configured"] is False and cleared["credentialLabel"] is None
    assert preferences.ai_settings().env_file is None


def test_selected_path_is_label_only_without_any_file_or_environment_discovery(tmp_path: Path, monkeypatch) -> None:
    import xfinaudio.ai.nan_client as client

    preferences = service(tmp_path)
    chosen = tmp_path / "never-read.env"
    snapshot = preferences.get_ai()
    before_environ = os.environ

    class NoDiscovery:
        def get(self, *args, **kwargs):
            raise AssertionError("AI settings must not inspect the environment")

        def __getitem__(self, key):
            raise AssertionError("AI settings must not inspect the environment")

    def forbidden(*args, **kwargs):
        raise AssertionError("Credential discovery/provider calls are forbidden")

    original_open = os.open

    def guarded_open(path, *args, **kwargs):
        if Path(path) == chosen:
            forbidden()
        return original_open(path, *args, **kwargs)

    original_stat = Path.stat

    def guarded_stat(path, *args, **kwargs):
        if path == chosen:
            forbidden()
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(client, "load_api_key_from_env_file", forbidden)
    monkeypatch.setattr(client, "default_env_file_path", forbidden)
    monkeypatch.setattr(client, "chat", forbidden)
    monkeypatch.setattr(client, "_urlopen", forbidden)
    monkeypatch.setattr(os, "open", guarded_open)
    monkeypatch.setattr(Path, "stat", guarded_stat)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(os, "environ", NoDiscovery())
    try:
        actual = preferences.set_ai_credential({"revision": snapshot["revision"], "path": chosen})
        assert actual["configured"] is True
        actual = preferences.update_ai({"revision": actual["revision"], "enabled": True})
        assert preferences.get_ai() == actual
        assert preferences.ai_settings().env_file == chosen
    finally:
        monkeypatch.setattr(os, "environ", before_environ)


@pytest.mark.parametrize(
    "patch",
    [
        {"enabled": 1},
        {"enabled": "true"},
        {"enabled": None},
        {"revision": None},
        {"revision": True},
        {"revision": "A" * 64},
        {"provider": "other"},
        {"path": "/private"},
        {"key": True},
    ],
)
def test_ai_update_rejects_untrusted_fields_without_settings_write(tmp_path: Path, patch: dict) -> None:
    preferences = service(tmp_path)
    revision = preferences.get_ai()["revision"]
    with pytest.raises(BackendError) as error:
        preferences.update_ai({"revision": revision, "enabled": False, **patch})
    assert error.value.code == "invalid_params"
    assert not (tmp_path / "settings.json").exists()


@pytest.mark.parametrize(
    "path", ["/absolute/string.env", Path("relative.env"), Path("/bad\x00.env"), Path("/" + "x" * 4096), True, 1]
)
def test_private_credential_selection_only_accepts_bounded_absolute_paths(tmp_path: Path, path) -> None:
    preferences = service(tmp_path)
    snapshot = preferences.get_ai()
    with pytest.raises(BackendError) as error:
        preferences.set_ai_credential({"revision": snapshot["revision"], "path": path})
    assert error.value.code == "invalid_params"
    assert preferences.get_ai() == snapshot
    assert not (tmp_path / "settings.json").exists()


@pytest.mark.parametrize(
    "method,params",
    [
        ("update_ai", {}),
        ("update_ai", {"enabled": True}),
        ("set_ai_credential", {}),
        ("set_ai_credential", {"revision": "0" * 64}),
        ("set_ai_credential", {"revision": False, "path": None}),
        ("set_ai_credential", {"revision": "0" * 64, "path": None, "enabled": True}),
    ],
)
def test_ai_methods_require_exact_fields(tmp_path: Path, method: str, params: dict) -> None:
    with pytest.raises(BackendError) as error:
        getattr(service(tmp_path), method)(params)
    assert error.value.code == "invalid_params"


@pytest.mark.parametrize("credential", [False, True])
def test_ai_and_other_preferences_share_revision_and_do_not_overwrite(tmp_path: Path, credential: bool) -> None:
    preferences = service(tmp_path)
    before = preferences.get_ai()
    other = service(tmp_path)
    shared = other.get_loudness()
    other.update_loudness({**shared, "targetLufs": -18})
    with pytest.raises(BackendError) as error:
        if credential:
            preferences.set_ai_credential({"revision": before["revision"], "path": tmp_path / "absent.env"})
        else:
            preferences.update_ai({"revision": before["revision"], "enabled": True})
    assert error.value.code == "stale_settings"
    assert preferences.get_loudness()["targetLufs"] == -18
    assert preferences.ai_settings() == AiSettings()


def test_ai_recovery_retains_bad_bytes_and_existing_pause_semantics(tmp_path: Path) -> None:
    preferences = service(tmp_path)
    (tmp_path / "settings.json").write_bytes(b"corrupt settings")
    assert preferences.get_ai()["enabled"] is False
    assert preferences.get_loudness()["enabled"] is False
    assert preferences.execute("settings.get", {})["recoveryWarning"] is True
    backups = list(tmp_path.glob("settings.json.recovery-*"))
    assert len(backups) == 1 and backups[0].read_bytes() == b"corrupt settings"


@pytest.mark.parametrize("entry", ["settings.json", ".settings.lock"])
def test_ai_settings_keep_nofollow_boundary(tmp_path: Path, entry: str) -> None:
    preferences = service(tmp_path / "data")
    victim = tmp_path / "outside.json"
    victim.write_bytes(b"original")
    (tmp_path / "data" / entry).symlink_to(victim)
    with pytest.raises(BackendError) as error:
        preferences.get_ai()
    assert error.value.code == "settings_unavailable" and victim.read_bytes() == b"original"


def test_credential_label_is_bounded_printable_basename(tmp_path: Path) -> None:
    preferences = service(tmp_path)
    chosen = Path("/private") / ("selected\n\t" + "x" * 300)
    result = preferences.set_ai_credential({"revision": preferences.get_ai()["revision"], "path": chosen})
    assert result["credentialLabel"].isprintable()
    assert len(result["credentialLabel"]) <= 200 and "/private" not in json.dumps(result)


def test_ai_module_and_neutral_query_import_without_desktop_or_qt() -> None:
    script = """
import importlib.abc, sys
class BlockDesktop(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'PySide6' or fullname.startswith(('PySide6.', 'xfinaudio.desktop')):
            raise AssertionError('Forbidden import: ' + fullname)
sys.meta_path.insert(0, BlockDesktop())
from xfinaudio.ai.structured_assists import LibraryQuery
from xfinaudio.application.library_query import LibraryQuery as NeutralQuery, parse_library_query
assert LibraryQuery is NeutralQuery
assert parse_library_query('House bpm 120-128', ['House']).bpm_min == 120
assert not any(name.startswith(('PySide6', 'xfinaudio.desktop')) for name in sys.modules)
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_legacy_query_facade_preserves_public_and_private_object_identities() -> None:
    from xfinaudio.application.library_query import LibraryQuery, _plain, parse_library_query

    path = Path(__file__).resolve().parents[1] / "src/xfinaudio/desktop/library_query.py"
    spec = importlib.util.spec_from_file_location("legacy_query_facade", path)
    assert spec is not None and spec.loader is not None
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    assert legacy.LibraryQuery is LibraryQuery
    assert legacy.parse_library_query is parse_library_query
    assert legacy._plain is _plain
    assert _plain("CANCIÓN") == "cancion"


def test_selected_label_is_safe_without_inspecting_the_credential(tmp_path):
    from xfinaudio.headless.backend import HeadlessBackend

    service = HeadlessBackend(tmp_path / "data").preferences
    status = service.get_ai()
    selected = service.set_ai_credential({"revision": status["revision"], "path": tmp_path / "dummy\\label.env"})
    assert "\\" not in selected["credentialLabel"]
