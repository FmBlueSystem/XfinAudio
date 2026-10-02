#!/usr/bin/env python3
"""Gated native Mac assembly; never sign with credentials or replace an install."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

from dependencies import audit_tree, dependency_closure, read_info, stage_closure

APP_EXECUTABLE = "XfinAudio Next"


def shared_tools(root: Path):
    spec = importlib.util.spec_from_file_location("linux_package", root / "packaging/linux/build.py")
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def validate_gate(report: dict, root: Path) -> str:
    """Cross-host owner evidence keeps its original root; exact content is binding."""
    tools = shared_tools(root)
    origin = report.get("project_root", "")
    gates = {item["name"]: item for item in report.get("gates", [])}
    if (
        not isinstance(origin, str)
        or not Path(origin).is_absolute()
        or report.get("mode") != "run"
        or report.get("overall_status") != "passed"
        or report.get("source_sha256") != tools.source_digest(root)
        or not gates.keys() >= tools.REQUIRED_GATES
        or any(gates[n].get("status") != "passed" or gates[n].get("return_code") != 0 for n in tools.REQUIRED_GATES)
    ):
        raise ValueError("Complete exact-source owner gates are required")
    tools.validate_electron_gate(report.get("electron_tests", {}))
    return origin


def validate_environment(root: Path, installed: dict[str, str]) -> None:
    actual = dict(installed)
    if actual.pop("macholib", None) != "1.16.4":
        raise ValueError("Locked native Macholib required")
    shared_tools(root).validate_build_environment(root / "packaging/linux/requirements-build.txt", actual)


def freeze_command(root: Path, output: Path, ffmpeg: Path) -> list[str]:
    command = shared_tools(root).freeze_command(root, output, ffmpeg)
    command[-1] = str(root / "packaging/macos/core_entry.py")
    command.extend(
        [
            "--paths",
            str(root / "packaging/linux"),
            "--paths",
            str(root / "packaging/macos"),
            "--hidden-import",
            "mac_numba_cache",
            "--target-architecture",
            "arm64",
        ]
    )
    for library in sorted((ffmpeg.parent / "ffmpeg-libs").glob("*.dylib")):
        command.extend(["--add-binary", f"{library}:ffmpeg-libs"])
    return command


def assemble(root: Path, electron: Path, core: Path, destination: Path) -> None:
    if destination.exists() or destination.resolve().is_relative_to(root.resolve()):
        raise ValueError("App destination must be new and outside source")
    tools = shared_tools(Path(__file__).resolve().parents[2])
    required_notices = tools.platform_notices(root, electron, mac=True)
    package = json.loads((root / "desktop-electron/package.json").read_text())
    if (electron / "version").read_text().strip() != package["devDependencies"]["electron"]:
        raise ValueError("Electron version must match the source lock")
    for p in [
        electron / "Electron.app/Contents/MacOS/Electron",
        core / "xfinaudio-core",
        core / "_internal/ffmpeg",
        root / "desktop-electron/.out/main/main.js",
        root / "desktop-electron/.out/renderer/index.html",
    ]:
        if not p.is_file():
            raise ValueError("Missing compiled runtime input")
    shutil.copytree(electron / "Electron.app", destination, symlinks=True)
    # Electron 44 determines main-process packaged mode from the executable name.
    # Keeping the stock "Electron" name would select the development Python path.
    (destination / "Contents/MacOS/Electron").rename(destination / "Contents/MacOS" / APP_EXECUTABLE)
    resources = destination / "Contents/Resources"
    (resources / "default_app.asar").unlink(missing_ok=True)
    shutil.copytree(core, resources / "core", symlinks=True)
    app = resources / "app"
    app.mkdir()
    shutil.copytree(root / "desktop-electron/.out", app / ".out")
    (app / "package.json").write_text(
        json.dumps({"name": "xfinaudio-next", "version": package["version"], "main": ".out/main/main.js"}) + "\n"
    )
    licenses = resources / "LICENSES"
    licenses.mkdir()
    for source, target, _ in required_notices:
        shutil.copy2(source, resources / target)
    tools.verify_notices(required_notices, resources)
    plist = destination / "Contents/Info.plist"
    info = plistlib.loads(plist.read_bytes())
    info.update(
        CFBundleExecutable=APP_EXECUTABLE,
        CFBundleName="XfinAudio Next",
        CFBundleDisplayName="XfinAudio Next",
        CFBundleIdentifier="io.bluesystem.xfinaudio.next",
        CFBundleVersion=package["version"],
        CFBundleShortVersionString=package["version"],
    )
    plist.write_bytes(plistlib.dumps(info))


def validate_ffmpeg_manifest(binary: Path, manifest: dict) -> None:
    closure = dependency_closure(binary)
    expected = manifest.get("binaries", {})
    if set(map(str, closure)) != set(expected) or any(
        hashlib.sha256(p.read_bytes()).hexdigest() != expected[str(p)].get("sha256") for p in closure
    ):
        raise ValueError("Trusted FFmpeg closure differs from selected provenance")


def sign_and_record_final_manifest(destination: Path, source_sha256: str) -> None:
    """Audit delivered signed bytes without adding resources to the sealed app."""
    subprocess.run(["/usr/bin/codesign", "--force", "--deep", "--sign", "-", str(destination)], check=True)
    subprocess.run(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(destination)], check=True)
    core = destination / "Contents/Resources/core"
    manifest = {
        "source_sha256": source_sha256,
        "bundle": destination.name,
        "inventory_stage": "post-final-signing",
        "core_native_inventory": audit_tree(core, core / "xfinaudio-core"),
        "electron_native_inventory": audit_tree(
            destination, destination / "Contents/MacOS" / APP_EXECUTABLE, exclude=core
        ),
    }
    destination.with_name(destination.name + ".native-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["root", "output", "gate-report", "ffmpeg", "ffmpeg-manifest", "dependency-licenses"]:
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    root, output, binary = args.root.resolve(), args.output.resolve(), args.ffmpeg.resolve(strict=True)
    report = json.loads(args.gate_report.read_text())
    origin = validate_gate(report, root)
    if sys.platform != "darwin" or platform.machine() != "arm64" or "arm64" not in read_info(binary).architectures:
        raise ValueError("Native Darwin arm64 inputs required")
    if output.exists() or output.is_relative_to(root):
        raise ValueError("Build workspace must be new and outside source")
    if not args.dependency_licenses.is_dir() or not any(args.dependency_licenses.iterdir()):
        raise ValueError("Explicit third-party license material required")
    validate_environment(root, {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()})
    electron = root / "desktop-electron/node_modules/electron/dist"
    if "arm64" not in read_info(electron / "Electron.app/Contents/MacOS/Electron").architectures:
        raise ValueError("Native Electron arm64 required")
    manifest = json.loads(args.ffmpeg_manifest.read_text())
    validate_ffmpeg_manifest(binary, manifest)
    tools = shared_tools(root)
    required_notices = tools.python_notices()
    platform_required_notices = tools.platform_notices(root, electron, mac=True)
    output.mkdir(parents=True)
    decoder = stage_closure(binary, output / "decoder")
    subprocess.run(
        freeze_command(root, output, decoder),
        cwd=root,
        check=True,
        env=tools.freeze_environment(dict(os.environ), output),
    )
    core = output / "core-dist/xfinaudio-core"
    modules = tools.audit_frozen_core(core / "xfinaudio-core")
    tools.audit_tree(core)
    inventory = audit_tree(core, core / "xfinaudio-core")
    subprocess.run(["npm", "run", "build"], cwd=root / "desktop-electron", check=True)
    validate_gate(report, root)
    destination = output / "XfinAudio Next.app"
    tools.verify_notices(required_notices, core / "_internal")
    assemble(root, electron, core, destination)
    resources = destination / "Contents/Resources"
    tools.verify_notices(required_notices, resources / "core/_internal")
    shutil.copytree(args.dependency_licenses, resources / "LICENSES/FFmpeg-dependencies")
    shutil.copy2(args.ffmpeg_manifest, resources / "LICENSES/ffmpeg-input-provenance.json")
    shutil.copy2(args.gate_report, resources / "release-gate.json")
    provenance = {
        "source_sha256": tools.source_digest(root),
        "gate_origin_project_root": origin,
        "python": platform.python_version(),
        "architecture": platform.machine(),
        "frozen_modules": modules,
        "inventory_stage": "pre-final-signing",
        "core_native_inventory": inventory,
        "signature": "local ad-hoc integrity only; no Developer ID/notarization",
    }
    (resources / "build-provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    tools.audit_tree(destination)
    audit_tree(resources / "core", resources / "core/xfinaudio-core")
    electron_inventory = audit_tree(
        destination, destination / "Contents/MacOS" / APP_EXECUTABLE, exclude=resources / "core"
    )
    provenance["electron_native_inventory"] = electron_inventory
    (resources / "build-provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    sign_and_record_final_manifest(destination, provenance["source_sha256"])
    tools.verify_notices(platform_required_notices, resources)
    tools.verify_notices(required_notices, resources / "core/_internal")
    validate_gate(report, root)
    validate_ffmpeg_manifest(binary, manifest)
    print(destination)


if __name__ == "__main__":
    main()
