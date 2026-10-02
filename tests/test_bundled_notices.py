"""Retain bounded wheel notices and fail closed on missing or altered evidence."""

import hashlib
import importlib.metadata
import importlib.util
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
VENDORS = (
    "autocommand-2.2.2.dist-info/LICENSE",
    "backports.tarfile-1.2.0.dist-info/LICENSE",
    "importlib_metadata-8.7.1.dist-info/licenses/LICENSE",
    "jaraco.text-4.0.0.dist-info/LICENSE",
    "jaraco_context-6.1.0.dist-info/licenses/LICENSE",
    "jaraco_functools-4.4.0.dist-info/licenses/LICENSE",
    "more_itertools-10.8.0.dist-info/licenses/LICENSE",
    "packaging-26.0.dist-info/licenses/LICENSE",
    "packaging-26.0.dist-info/licenses/LICENSE.APACHE",
    "packaging-26.0.dist-info/licenses/LICENSE.BSD",
    "platformdirs-4.4.0.dist-info/licenses/LICENSE",
    "tomli-2.4.0.dist-info/licenses/LICENSE",
    "wheel-0.46.3.dist-info/licenses/LICENSE.txt",
    "zipp-3.23.0.dist-info/licenses/LICENSE",
)
INPUTS = {
    "soundfile": (
        "0.14.0",
        ("licensing/license_notes.md", "_soundfile_data/COPYING", "soundfile-0.14.0.dist-info/LICENSE"),
    ),
    "setuptools": (
        "82.0.1",
        (
            "setuptools-82.0.1.dist-info/licenses/LICENSE",
            "setuptools/config/NOTICE",
            "setuptools/config/_validate_pyproject/NOTICE",
            *("setuptools/_vendor/" + name for name in VENDORS),
        ),
    ),
}


def module():
    spec = importlib.util.spec_from_file_location("notice_build", ROOT / "packaging/linux/build.py")
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


@pytest.fixture
def environment(tmp_path, monkeypatch):
    site = tmp_path / "site-packages"
    distributions = {}
    for name, (version, paths) in INPUTS.items():
        for rel in paths:
            path = site / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"Copyright\r\n" + rel.encode() + b"\n\xff")
        distributions[name] = SimpleNamespace(
            version=version,
            files=[Path(p) for p in (*paths, "arbitrary-code.py")],
            locate_file=lambda rel: site / rel,
        )
    monkeypatch.setattr(importlib.metadata, "distribution", lambda name: distributions[name])
    return site, distributions


def test_freeze_retains_exact_notice_bytes_and_provenance_without_package_trees(tmp_path, environment):
    pack = module()
    lock = tmp_path / "desktop-electron/requirements-headless.txt"
    lock.parent.mkdir()
    lock.write_text("soundfile==0.14.0\n")
    records = pack.python_notices()
    expected = {
        Path(f"licenses/bundled/{name}-{version}/{rel}") for name, (version, paths) in INPUTS.items() for rel in paths
    }
    assert {target for _, target, _ in records} == expected
    command = pack.freeze_command(tmp_path, tmp_path / "output", tmp_path / "ffmpeg")
    for source, target, digest in records:
        assert digest == hashlib.sha256(source.read_bytes()).hexdigest()
        assert f"{source}:{target.parent.as_posix()}" in command
        copied = tmp_path / "core" / target
        copied.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, copied)
        assert copied.read_bytes() == source.read_bytes()
    pack.verify_notices(records, tmp_path / "core")
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("name,rel", [(name, rel) for name, (_, paths) in INPUTS.items() for rel in paths])
@pytest.mark.parametrize("failure", ["missing", "empty", "unrecorded", "escape"])
def test_required_notices_fail_closed(tmp_path, environment, name, rel, failure):
    site, distributions = environment
    path = site / rel
    if failure == "unrecorded":
        distributions[name].files.remove(Path(rel))
    elif failure == "empty":
        path.write_bytes(b"")
    else:
        path.unlink()
        if failure == "escape":
            external = tmp_path / "external"
            external.write_bytes(b"not selected input")
            path.symlink_to(external)
    with pytest.raises(ValueError, match="notice"):
        module().python_notices()


@pytest.mark.parametrize("failure", ["version", "record"])
def test_unavailable_locked_distribution_metadata_fails(environment, failure):
    _, distributions = environment
    if failure == "version":
        distributions["setuptools"].version = "unexpected"
    else:
        distributions["setuptools"].files = None
    with pytest.raises(ValueError, match="notice"):
        module().python_notices()


@pytest.mark.parametrize("content", [None, b"", b"altered notice"])
def test_final_notice_verification_detects_missing_empty_or_altered_bytes(tmp_path, environment, content):
    pack = module()
    records = pack.python_notices()
    for source, target, _ in records:
        copied = tmp_path / "delivered" / target
        copied.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, copied)
    changed = tmp_path / "delivered" / records[0][1]
    if content is None:
        changed.unlink()
    else:
        changed.write_bytes(content)
    with pytest.raises(ValueError, match="notice"):
        pack.verify_notices(records, tmp_path / "delivered")
