#!/usr/bin/env python3
"""Fail-closed, relocatable Linux Electron/Python assembly; never publish artifacts."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

REQUIRED_GATES = {
    "tests and coverage",
    "type-check",
    "lint",
    "format",
    "release readiness smoke",
    "open-source publication docs",
    "publication artifact hygiene",
    "source package hygiene",
    "PyInstaller check-only",
    "root artifact hygiene",
}
EXCLUDES = ("PySide6", "PySide2", "PyQt6", "PyQt5", "qtpy", "shiboken6", "shiboken2", "xfinaudio.desktop")
GENERATED = {
    ".git",
    ".out",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".venv-headless",
    ".release-evidence",
    "build",
    "dist",
    "htmlcov",
}


def source_digest(root: Path) -> str:
    """Hash every source file, including untracked additions, excluding generated trees."""
    digest = hashlib.sha256()
    for directory, names, files in os.walk(root):
        names[:] = sorted(name for name in names if name not in GENERATED)
        for name in sorted([*names, *files]):
            path = Path(directory) / name
            if name.startswith(".coverage"):
                continue
            if path.is_symlink():
                raise ValueError(f"Unexpected source symlink: {path}")
            if path.is_file():
                relative = path.relative_to(root).as_posix().encode()
                digest.update(len(relative).to_bytes(8, "big") + relative)
                digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def validate_gate(report: dict, root: Path) -> None:
    """Require the complete aggregate, successful execution, and an exact source seal."""
    gates = {item["name"]: item for item in report.get("gates", [])}
    if (
        report.get("mode") != "run"
        or report.get("overall_status") != "passed"
        or Path(report.get("project_root", "")).resolve() != root.resolve()
        or report.get("source_sha256") != source_digest(root)
        or not gates.keys() >= REQUIRED_GATES
        or any(gates[name].get("status") != "passed" or gates[name].get("return_code") != 0 for name in REQUIRED_GATES)
    ):
        raise ValueError("A complete passing exact-source release gate is required")


def validate_electron_gate(report: dict) -> None:
    if (
        report.get("status") != "passed"
        or type(report.get("passed")) is not int
        or report["passed"] < 1
        or report.get("failed") != 0
        or report.get("skipped") != 0
    ):
        raise ValueError("Passing Electron tests with real integrations and zero skips are required")


def validate_build_environment(lock: Path, installed: dict[str, str]) -> None:
    def normalize(name: str) -> str:
        return re.sub(r"[-_.]+", "-", name).lower()

    expected = {
        normalize(name): version
        for name, version in re.findall(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s\\]+)", lock.read_text(), re.MULTILINE)
    }
    actual = {normalize(name): version for name, version in installed.items()}
    if not expected or expected != actual:
        raise ValueError("Freezer environment must exactly match the hash-locked build requirements")


def assert_core_modules(names) -> None:
    bad = [name for name in names if any(name == excluded or name.startswith(excluded + ".") for excluded in EXCLUDES)]
    if bad:
        raise ValueError(f"Qt/legacy desktop modules forbidden: {bad}")


def audit_tree(root: Path) -> None:
    for path in root.rglob("*"):
        if path.is_symlink() and (
            Path(os.readlink(path)).is_absolute() or not path.resolve().is_relative_to(root.resolve())
        ):
            raise ValueError(f"External runtime symlink: {path}")
        if any(
            part == "node_modules" or part.lower().startswith(("libqt", "pyside", "pyqt", "shiboken"))
            for part in path.relative_to(root).parts
        ):
            raise ValueError(f"Qt/development artifact forbidden: {path}")


def freeze_command(root: Path, output: Path, ffmpeg: Path) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onedir",
        "--contents-directory",
        "_internal",
        "--name",
        "xfinaudio-core",
        "--noupx",
        "--paths",
        str(root / "src"),
        "--distpath",
        str(output / "core-dist"),
        "--workpath",
        str(output / "core-work"),
        "--specpath",
        str(output / "core-spec"),
        "--collect-submodules",
        "mutagen",
        "--add-binary",
        f"{ffmpeg}:.",
    ]
    locked = (root / "desktop-electron/requirements-headless.txt").read_text()
    packages = set(re.findall(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==", locked, re.MULTILINE))
    if "scipy" in packages:
        for module in ("fft", "linalg"):
            command.extend(["--hidden-import", f"scipy._external.array_api_compat.numpy.{module}"])
    if "librosa" in packages:
        command.extend(["--collect-all", "librosa"])
    for package in sorted(packages | {"pyinstaller"}):
        command.extend(["--copy-metadata", package])
    license_path = (
        Path(sys.base_prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "LICENSE.txt"
    )
    command.extend(["--add-data", f"{license_path}:licenses/python"])
    for excluded in EXCLUDES:
        command.extend(["--exclude-module", excluded])
    return [*command, str(root / "packaging/linux/core_entry.py")]


def freeze_environment(parent: dict[str, str], output: Path) -> dict[str, str]:
    return {**parent, "PYINSTALLER_CONFIG_DIR": str(output / "pyinstaller-cache")}


def assemble(root: Path, electron: Path, core: Path, destination: Path) -> None:
    """Only consume explicit runtime inputs; refuse missing dependencies and overwrites."""
    if destination.exists() or destination.resolve().is_relative_to(root.resolve()):
        raise ValueError("Output must be a new directory outside the source tree")
    package = json.loads((root / "desktop-electron/package.json").read_text())
    if (electron / "version").read_text().strip() != package["devDependencies"]["electron"]:
        raise ValueError("Electron distribution does not match package lock version")
    for executable in (electron / "electron", core / "xfinaudio-core", core / "_internal/ffmpeg"):
        if not executable.is_file() or not os.access(executable, os.X_OK):
            raise ValueError(f"Missing executable runtime dependency: {executable}")
    if not list((core / "_internal").glob("libpython3*.so*")):
        raise ValueError("Bundled Python shared library missing")
    for tree in (electron, core, root / "desktop-electron/.out"):
        audit_tree(tree)
    shutil.copytree(electron, destination, symlinks=True)
    (destination / "electron").rename(destination / "xfinaudio")
    (destination / "resources/default_app.asar").unlink(missing_ok=True)
    app = destination / "resources/app"
    app.mkdir()
    shutil.copytree(root / "desktop-electron/.out", app / ".out")
    manifest = {
        "name": "xfinaudio",
        "version": package["version"],
        "private": True,
        "main": ".out/main/main.js",
        "license": "GPL-3.0-only",
    }
    (app / "package.json").write_text(json.dumps(manifest, indent=2) + "\n")
    shutil.copytree(core, destination / "resources/core", symlinks=True)
    notices = destination / "LICENSES"
    notices.mkdir()
    shutil.copy2(root / "LICENSE", notices / "XfinAudio-LICENSE")
    shutil.copy2(root / "NOTICE.md", notices / "XfinAudio-NOTICE.md")
    audit_tree(destination)


def audit_frozen_core(executable: Path) -> list[str]:
    from PyInstaller.archive.readers import CArchiveReader

    archive = CArchiveReader(str(executable))
    modules = sorted(archive.open_embedded_archive("PYZ.pyz").toc)
    assert_core_modules(modules)
    return modules


def _probe(args: list[str]) -> str:
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout


def validate_ffmpeg(binary: Path, probe=_probe) -> None:
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise ValueError("FFmpeg executable missing")
    commands = {
        "-version": ("ffmpeg version 7.1.1", "--disable-network"),
        "-filters": ("ebur128",),
        "-decoders": ("aac", "alac", "flac", "mp3", "pcm_s16le"),
        "-demuxers": ("aiff", "flac", "mp3", "mov", "wav"),
        "-muxers": ("null", "s16le"),
        "-encoders": ("pcm_s16le",),
    }
    for option, required in commands.items():
        text = probe([str(binary), "-hide_banner", option])
        if not all(item in text for item in required):
            raise ValueError(f"FFmpeg capability missing: {option}")
    help_text = probe([str(binary), "-hide_banner", "-h", "filter=ebur128"])
    if "peak" not in help_text or "true" not in help_text:
        raise ValueError("FFmpeg true peak support missing")


def validate_ffmpeg_dependencies(text: str) -> None:
    allowed = ("linux-vdso.so.", "libc.so.", "libm.so.", "/lib64/ld-linux-x86-64.so.")
    if not text.strip() or any(
        not line.strip().startswith(allowed) or "not found" in line for line in text.splitlines() if line.strip()
    ):
        raise ValueError("FFmpeg must use only the declared baseline Linux C/math/loader libraries")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gate-report", type=Path, required=True)
    parser.add_argument("--ffmpeg", type=Path, required=True)
    parser.add_argument("--ffmpeg-source", type=Path, required=True)
    args = parser.parse_args()
    root, output, ffmpeg = args.root.resolve(), args.output.resolve(), args.ffmpeg.resolve()
    report = json.loads(args.gate_report.read_text())
    validate_gate(report, root)
    validate_electron_gate(report.get("electron_tests", {}))
    if sys.platform != "linux" or platform.machine() != "x86_64":
        raise ValueError("This recipe is Linux x86_64 only")
    if output.exists() or output.is_relative_to(root):
        raise ValueError("Build workspace must be new and outside source")
    import PyInstaller

    if PyInstaller.__version__ != "6.20.0":
        raise ValueError("PyInstaller 6.20.0 required")
    validate_build_environment(
        root / "packaging/linux/requirements-build.txt",
        {item.metadata["Name"]: item.version for item in importlib.metadata.distributions()},
    )
    source_lock = json.loads((root / "packaging/linux/ffmpeg-source.json").read_text())
    if hashlib.sha256(args.ffmpeg_source.read_bytes()).hexdigest() != source_lock["sha256"]:
        raise ValueError("FFmpeg source archive checksum mismatch")
    validate_ffmpeg(ffmpeg)
    validate_ffmpeg_dependencies(_probe(["ldd", str(ffmpeg)]))
    output.mkdir(parents=True)
    subprocess.run(
        freeze_command(root, output, ffmpeg), check=True, cwd=root, env=freeze_environment(dict(os.environ), output)
    )
    core = output / "core-dist/xfinaudio-core"
    modules = audit_frozen_core(core / "xfinaudio-core")
    subprocess.run(["npm", "run", "build"], check=True, cwd=root / "desktop-electron")
    validate_gate(report, root)
    destination = output / "XfinAudio-linux-x86_64"
    assemble(root, root / "desktop-electron/node_modules/electron/dist", core, destination)
    shutil.copy2(args.ffmpeg_source, destination / "LICENSES" / args.ffmpeg_source.name)
    with tarfile.open(args.ffmpeg_source) as archive:
        license_file = archive.extractfile("ffmpeg-7.1.1/COPYING.LGPLv2.1")
        if license_file is None:
            raise ValueError("FFmpeg license missing from source archive")
        (destination / "LICENSES/FFmpeg-LGPL-2.1.txt").write_bytes(license_file.read())
    shutil.copy2(
        root / "desktop-electron/requirements-headless.txt", destination / "LICENSES/requirements-headless.txt"
    )
    for name in ("ffmpeg-source.json", "ffmpeg-configure.args", "README.md", "requirements-build.txt"):
        shutil.copy2(root / "packaging/linux" / name, destination / "LICENSES" / name)
    provenance = {
        "source_sha256": source_digest(root),
        "platform": platform.platform(),
        "libc": platform.libc_ver(),
        "python": platform.python_version(),
        "pyinstaller": PyInstaller.__version__,
        "electron": "44.5.1",
        "ffmpeg": source_lock,
        "ffmpeg_binary_sha256": hashlib.sha256(ffmpeg.read_bytes()).hexdigest(),
        "frozen_modules": modules,
    }
    (destination / "build-provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    shutil.copy2(args.gate_report, destination / "release-gate.json")
    validate_gate(report, root)
    archive = output / "XfinAudio-linux-x86_64.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(destination, arcname=destination.name)
    archive.with_suffix(archive.suffix + ".sha256").write_text(
        hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n"
    )
    print(archive)


if __name__ == "__main__":
    main()
