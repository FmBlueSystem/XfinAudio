"""Execute the actual DMG shell pipeline using synthetic Linux tools only."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_release_provenance import git

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FAKE_TOOLS = r"""
import os, pathlib, plistlib, subprocess, sys, tomllib
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
log = pathlib.Path(os.environ["TOOL_LOG"])
def event(text):
    with log.open("a") as stream: stream.write(text + "\n")
if name == "uv":
    args = [arg for arg in args if arg not in ("run", "--locked")]
    if args[0] == "python":
        if pathlib.Path(args[1]).name == "release_gate_check.py":
            event("gate")
            if os.environ.get("CHANGE_SOURCE") == "gate":
                pathlib.Path("pyproject.toml").write_text("changed")
            if os.environ.get("CHANGE_COMMIT"):
                subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                                "commit", "--allow-empty", "--quiet", "-m", "new commit"], check=True)
            sys.exit(int(os.environ.get("FAIL_GATE", "0")))
        os.execv(sys.executable, [sys.executable, *args[1:]])
    assert args[0] == "pyinstaller", args
    event("build")
    if os.environ.get("FAIL_BUILD"): sys.exit(1)
    app = pathlib.Path(args[args.index("--distpath") + 1]) / "XfinAudio.app"
    binary = app / "Contents/MacOS/XfinAudio"
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_text('#!/bin/sh\nprintf "smoke\\n" >> "$TOOL_LOG"\nexit "${FAIL_SMOKE:-0}"\n')
    binary.chmod(0o755)
    version = tomllib.loads(pathlib.Path("pyproject.toml").read_text())["project"]["version"]
    (app / "Contents/Info.plist").write_bytes(plistlib.dumps({"CFBundleShortVersionString": version}))
    if os.environ.get("CHANGE_SOURCE") == "build":
        pathlib.Path("pyproject.toml").write_text("changed")
elif name == "security":
    pass
elif name in ("codesign", "spctl", "xcrun"):
    event(name)
    if os.environ.get("FAIL_TOOL") == name: sys.exit(1)
elif name == "hdiutil":
    event("image:" + args[0])
    if args[0] == "create": pathlib.Path(args[-1]).write_text("synthetic image")
else:
    raise AssertionError(name)
"""


@pytest.fixture
def pipeline(tmp_path: Path) -> tuple[Path, dict[str, str], Path]:
    root = tmp_path / "source"
    (root / "scripts").mkdir(parents=True)
    for name in ("build_dmg.sh", "release_provenance.py"):
        shutil.copy2(PROJECT_ROOT / "scripts" / name, root / "scripts" / name)
    (root / "pyproject.toml").write_text('[other]\nversion = "wrong"\n[project]\nversion = "1.2.3"\n')
    (root / ".gitignore").write_text("out/\n")
    git(root, "init", "--quiet")
    git(root, "add", ".")
    git(root, "commit", "--quiet", "-m", "fixture")
    tools = tmp_path / "tools"
    tools.mkdir()
    for name in ("uv", "security", "codesign", "spctl", "xcrun", "hdiutil"):
        tool = tools / name
        tool.write_text(f"#!{sys.executable}\n{FAKE_TOOLS}")
        tool.chmod(0o755)
    log = tmp_path / "tools.log"
    env = {
        **os.environ,
        "PATH": f"{tools}:{os.environ['PATH']}",
        "TOOL_LOG": str(log),
        "XFINAUDIO_SIGN_IDENTITY": "",
        "XFINAUDIO_NOTARY_PROFILE": "",
        "SKIP_APP_BUILD": "0",
    }
    return root, env, log


def run(pipeline: tuple[Path, dict[str, str], Path], **changes: str) -> subprocess.CompletedProcess[str]:
    root, env, _ = pipeline
    return subprocess.run(
        ["bash", "scripts/build_dmg.sh", "out"], cwd=root, env={**env, **changes}, text=True, capture_output=True
    )


def events(pipeline: tuple[Path, dict[str, str], Path]) -> list[str]:
    return pipeline[2].read_text().splitlines() if pipeline[2].exists() else []


def test_fresh_build_and_reuse_enforce_gate_and_integrity(pipeline) -> None:
    result = run(pipeline)
    assert result.returncode == 0, result.stderr
    assert events(pipeline) == ["gate", "build", "smoke", "image:create", "image:verify"]
    root = pipeline[0]
    assert (root / "out/XfinAudio-1.2.3.dmg").is_file()
    evidence = root / "out/dist/XfinAudio.app.provenance.json"
    assert json.loads(evidence.read_text())["source_commit"] == git(root, "rev-parse", "HEAD")
    pipeline[2].unlink()
    result = run(pipeline, SKIP_APP_BUILD="1")
    assert result.returncode == 0, result.stderr
    assert events(pipeline) == ["gate", "smoke", "image:create", "image:verify"]


@pytest.mark.parametrize("change", [{"FAIL_GATE": "7"}, {"CHANGE_SOURCE": "gate"}, {"CHANGE_COMMIT": "1"}])
def test_failed_or_changed_gate_stops_before_build(pipeline, change) -> None:
    result = run(pipeline, **change)
    assert result.returncode != 0
    assert events(pipeline) == ["gate"]


def test_dirty_source_stops_before_gate(pipeline) -> None:
    (pipeline[0] / "untracked.py").write_text("changed")
    assert run(pipeline).returncode != 0
    assert events(pipeline) == []


@pytest.mark.parametrize("change", [{"FAIL_BUILD": "1"}, {"CHANGE_SOURCE": "build"}, {"FAIL_SMOKE": "1"}])
def test_failed_build_smoke_or_changed_source_never_records_or_packages(pipeline, change) -> None:
    assert run(pipeline, **change).returncode != 0
    assert "image:create" not in events(pipeline)
    assert not (pipeline[0] / "out/dist/XfinAudio.app.provenance.json").exists()


@pytest.mark.parametrize("mutation", ["missing", "malformed", "tamper", "commit"])
def test_bad_reuse_stops_before_execution_or_signing(pipeline, mutation) -> None:
    assert run(pipeline).returncode == 0
    root = pipeline[0]
    evidence = root / "out/dist/XfinAudio.app.provenance.json"
    if mutation == "missing":
        evidence.unlink(missing_ok=True)
    elif mutation == "malformed":
        evidence.write_text("[]")
    elif mutation == "tamper":
        (root / "out/dist/XfinAudio.app/extra").write_text("tamper")
    else:
        git(root, "commit", "--allow-empty", "--quiet", "-m", "different source")
    pipeline[2].unlink()
    result = run(pipeline, SKIP_APP_BUILD="1", XFINAUDIO_SIGN_IDENTITY="SYNTHETIC")
    assert result.returncode != 0
    assert events(pipeline) == ["gate"]


def test_notary_still_requires_signing_identity(pipeline) -> None:
    assert run(pipeline, XFINAUDIO_NOTARY_PROFILE="SYNTHETIC").returncode != 0
    assert events(pipeline) == []


@pytest.mark.parametrize("failed_tool", ["", "codesign", "spctl", "xcrun"])
def test_optional_sign_and_notary_still_propagate_failure(pipeline, failed_tool) -> None:
    result = run(
        pipeline, XFINAUDIO_SIGN_IDENTITY="SYNTHETIC", XFINAUDIO_NOTARY_PROFILE="SYNTHETIC", FAIL_TOOL=failed_tool
    )
    assert (result.returncode == 0) == (not failed_tool)
    if not failed_tool:
        assert events(pipeline).count("codesign") == 2
        assert events(pipeline).count("xcrun") == 3
