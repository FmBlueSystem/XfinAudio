"""Offline provenance checks using temporary repositories and synthetic bundles."""

from __future__ import annotations

import importlib.util
import json
import os
import plistlib
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "release_provenance.py"


@pytest.fixture
def provenance() -> ModuleType:
    assert SCRIPT.is_file(), "Release provenance enforcement is missing"
    spec = importlib.util.spec_from_file_location("release_provenance", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def source(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    root.mkdir()
    git(root, "init", "--quiet")
    (root / "pyproject.toml").write_text('[unrelated]\nversion = "wrong"\n[project]\nversion = "1.2.3"\n')
    (root / ".gitignore").write_text("out/\n")
    git(root, "add", ".")
    git(root, "commit", "--quiet", "-m", "fixture")
    return root


@pytest.fixture
def bundle(tmp_path: Path) -> Path:
    app = tmp_path / "XfinAudio.app"
    executable = app / "Contents" / "MacOS" / "XfinAudio"
    executable.parent.mkdir(parents=True)
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)
    (app / "Contents" / "Info.plist").write_bytes(plistlib.dumps({"CFBundleShortVersionString": "1.2.3"}))
    (app / "launch").symlink_to("Contents/MacOS/XfinAudio")
    return app


@pytest.mark.parametrize("change", ["tracked", "staged", "untracked"])
def test_source_rejects_dirty_checkout(provenance: ModuleType, source: Path, change: str) -> None:
    assert provenance.source_commit(source) == git(source, "rev-parse", "HEAD")
    path = source / ("new.py" if change == "untracked" else "pyproject.toml")
    path.write_text("changed")
    if change == "staged":
        git(source, "add", ".")
    with pytest.raises(provenance.ProvenanceError, match="clean"):
        provenance.source_commit(source)


def test_source_rejects_wrong_commit_and_non_repository(provenance: ModuleType, source: Path, tmp_path: Path) -> None:
    with pytest.raises(provenance.ProvenanceError, match="changed"):
        provenance.source_commit(source, "0" * 40)
    with pytest.raises(subprocess.CalledProcessError):
        provenance.source_commit(tmp_path)


def test_round_trip_pins_source_version_and_content(provenance: ModuleType, source: Path, bundle: Path) -> None:
    commit = provenance.source_commit(source)
    evidence = bundle.with_suffix(".provenance.json")
    provenance.record(source, bundle, commit, evidence)
    provenance.verify(source, bundle, commit, evidence)
    data = json.loads(evidence.read_text())
    assert data["source_commit"] == commit
    assert data["project_version"] == "1.2.3"
    assert data["gate_command"] == ["uv", "run", "python", "scripts/release_gate_check.py", "--run"]
    assert len(data["bundle_sha256"]) == 64


@pytest.mark.parametrize("mutation", ["content", "add", "remove", "mode", "link", "commit", "version"])
def test_reuse_rejects_mismatched_provenance(provenance: ModuleType, source: Path, bundle: Path, mutation: str) -> None:
    commit = provenance.source_commit(source)
    evidence = bundle.with_suffix(".provenance.json")
    provenance.record(source, bundle, commit, evidence)
    executable = bundle / "Contents/MacOS/XfinAudio"
    if mutation == "content":
        executable.write_text("replaced")
    elif mutation == "add":
        (bundle / "extra").write_text("extra")
    elif mutation == "remove":
        (bundle / "launch").unlink()
    elif mutation == "mode":
        executable.chmod(0o644)
    elif mutation == "link":
        (bundle / "launch").unlink()
        (bundle / "launch").symlink_to("Contents/Info.plist")
    else:
        if mutation == "version":
            project = source / "pyproject.toml"
            project.write_text(project.read_text().replace("1.2.3", "1.2.4"))
            git(source, "add", ".")
        git(source, "commit", "--allow-empty", "--quiet", "-m", "new commit")
        commit = provenance.source_commit(source)
    with pytest.raises(provenance.ProvenanceError):
        provenance.verify(source, bundle, commit, evidence)


@pytest.mark.parametrize("raw", [None, "invalid json", "[]", "{}", '{"schema_version": 999}'])
def test_reuse_fails_without_valid_evidence(
    provenance: ModuleType, source: Path, bundle: Path, raw: str | None
) -> None:
    evidence = bundle.with_suffix(".provenance.json")
    if raw is not None:
        evidence.write_text(raw)
    with pytest.raises((provenance.ProvenanceError, OSError, ValueError)):
        provenance.verify(source, bundle, provenance.source_commit(source), evidence)


@pytest.mark.parametrize("kind", ["outside", "broken", "fifo", "bundle_link", "wrong_version"])
def test_unsafe_bundle_is_not_recorded(
    provenance: ModuleType, source: Path, bundle: Path, tmp_path: Path, kind: str
) -> None:
    if kind == "outside":
        (bundle / "escape").symlink_to(source / "pyproject.toml")
    elif kind == "broken":
        (bundle / "escape").symlink_to("missing")
    elif kind == "fifo":
        os.mkfifo(bundle / "fifo")
    elif kind == "bundle_link":
        link = tmp_path / "linked.app"
        link.symlink_to(bundle, target_is_directory=True)
        bundle = link
    else:
        (bundle / "Contents/Info.plist").write_bytes(plistlib.dumps({"CFBundleShortVersionString": "9.9.9"}))
    evidence = tmp_path / "evidence.json"
    with pytest.raises(provenance.ProvenanceError):
        provenance.record(source, bundle, provenance.source_commit(source), evidence)
    assert not evidence.exists()


@pytest.mark.parametrize("relative", [".", "build", "dist", "build/nested", "dist/nested"])
def test_output_cannot_create_root_artifacts(provenance: ModuleType, source: Path, relative: str) -> None:
    with pytest.raises(provenance.ProvenanceError, match="output"):
        provenance.output_directory(source, source / relative)
    assert not (source / "build").exists()
    assert not (source / "dist").exists()
