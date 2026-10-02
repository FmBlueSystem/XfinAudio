"""Mac-only frozen locator retains original stamps and confines all code cache."""

import hashlib
import importlib.util
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    sys.path.insert(0, str(ROOT / "packaging/linux"))
    location = ROOT / "packaging/macos" / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, location)
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_mac_overrides_hostile_locators_before_scientific_import(tmp_path, monkeypatch):
    bootstrap = module("mac_runtime_bootstrap")
    data = tmp_path.resolve() / "app"
    before = dict(os.environ)
    with monkeypatch.context() as context:
        for key in ["PATH", "NUMBA_CACHE_DIR", "NUMBA_CACHE_LOCATOR_CLASSES", "XDG_CACHE_HOME", "LIBROSA_CACHE_DIR"]:
            context.setenv(key, "/never-access-hostile")
        bootstrap.configure_runtime(tmp_path.resolve() / "bundle", data)
        assert os.environ["NUMBA_CACHE_DIR"] == str(data / "cache/numba")
        assert os.environ["NUMBA_CACHE_LOCATOR_CLASSES"] == "mac_numba_cache.AppDataCacheLocator"
        assert "LIBROSA_CACHE_DIR" not in os.environ
        assert os.environ["PATH"] == str(tmp_path.resolve() / "bundle")
    assert dict(os.environ) == before


def test_direct_locator_frozen_stamp_preserves_original_invalidation(tmp_path, monkeypatch):
    locator = module("mac_numba_cache")
    from numba import config

    cache = tmp_path.resolve() / "app/cache/numba"
    monkeypatch.setattr(config, "CACHE_DIR", str(cache))
    executable = tmp_path / "frozen-core"
    executable.write_bytes(b"first executable bytes")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))

    def function():
        return 1

    value = locator.AppDataCacheLocator.from_function(function, "relative/frozen-module.py")
    assert value is not None
    assert Path(value.get_cache_path()).is_relative_to(cache)
    # The legacy aggregate uses Numba 0.65; the hash-locked standalone runtime
    # uses 0.68. Preserve the actual base implementation in both environments.
    original = locator.UserWideCacheLocator(function, "relative/frozen-module.py")
    first_stamp = original.get_source_stamp()
    assert value.get_source_stamp() == first_stamp
    if isinstance(first_stamp, bytes):
        assert first_stamp == hashlib.sha256(executable.read_bytes()).digest()
    executable.write_bytes(b"different executable version bytes")
    next_stamp = original.get_source_stamp()
    assert next_stamp != first_stamp
    assert value.get_source_stamp() == next_stamp
    if isinstance(next_stamp, bytes):
        assert next_stamp == hashlib.sha256(executable.read_bytes()).digest()
    assert value.get_disambiguator() == str(function.__code__.co_firstlineno)
    assert not (tmp_path / "Library").exists()


@pytest.mark.parametrize("kind", ["relative", "symlink", "file"])
def test_locator_rejects_unvalidated_cache(tmp_path, monkeypatch, kind):
    locator = module("mac_numba_cache")
    from numba import config

    p = tmp_path / "cache"
    if kind == "relative":
        value = "relative-cache"
    elif kind == "symlink":
        target = tmp_path / "elsewhere"
        target.mkdir()
        p.symlink_to(target, target_is_directory=True)
        value = str(p)
    else:
        p.write_bytes(b"not-directory")
        value = str(p)
    monkeypatch.setattr(config, "CACHE_DIR", value)
    with pytest.raises(ValueError):
        locator.AppDataCacheLocator(lambda: 1, "module.py")


def test_development_bootstrap_does_not_change_environment(tmp_path, monkeypatch):
    bootstrap = module("mac_runtime_bootstrap")
    monkeypatch.setenv("NUMBA_CACHE_LOCATOR_CLASSES", "DevelopmentLocator")
    before = dict(os.environ)
    bootstrap.configure_runtime(None)
    assert dict(os.environ) == before


def test_invalid_cli_or_data_symlink_creates_no_cache(tmp_path, monkeypatch):
    bootstrap = module("mac_runtime_bootstrap")
    target = tmp_path / "target"
    target.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError):
        bootstrap.configure_runtime(tmp_path / "bundle", alias)
    with pytest.raises(SystemExit):
        bootstrap.parse_data_dir(["--data-dir", str(target), "--unexpected"])
    assert not (target / "cache").exists()
