#!/usr/bin/env python3
"""Build the QA-only macOS disk image from an already-built, sealed app bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

IMAGE_NAME = "XfinAudio Next QA.dmg"
VOLUME_NAME = "XfinAudio Next QA"
APP_NAME = "XfinAudio Next.app"
EXECUTABLE = "XfinAudio Next"
SHA_NAME = "XfinAudio Next QA.sha256"
PROVENANCE_NAME = "XfinAudio Next QA.provenance.json"
MANIFEST_NAME = APP_NAME + ".native-manifest.json"
SOURCE_ROOT = Path(__file__).resolve().parents[2]
APPLICATIONS_LINK = "Applications"
APPLICATIONS_TARGET = "/Applications"
NOTICE_FILES = ("XfinAudio-NOTICE.md", "LICENSE", "LICENSES.chromium.html", "ffmpeg-input-provenance.json")
NOTICE_DIRS = ("FFmpeg-dependencies",)
CLEARANCE = (
    "ad-hoc local QA image; Developer ID signing, notarization, Gatekeeper approval and "
    "redistribution clearance were not evaluated"
)


def sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Hash a file of any size without holding it all in memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_source(app: Path, expected_source_sha256: str) -> str:
    if app.name != APP_NAME or not app.is_dir():
        raise ValueError(f"Input must be a built {APP_NAME}")
    executable = app / "Contents/MacOS" / EXECUTABLE
    if not executable.is_file() or not executable.stat().st_size:
        raise ValueError("Sealed app executable is missing")
    manifest_path = app.with_name(MANIFEST_NAME)
    record = json.loads(manifest_path.read_text())
    if (
        record.get("source_sha256") != expected_source_sha256
        or record.get("bundle") != APP_NAME
        or record.get("inventory_stage") != "post-final-signing"
    ):
        raise ValueError("Native manifest post-final-signing source seal/provenance mismatch")
    licenses = app / "Contents/Resources/LICENSES"
    for name in NOTICE_FILES:
        if not (licenses / name).is_file():
            raise ValueError(f"Declared notice is missing: {name}")
    for name in NOTICE_DIRS:
        if not (licenses / name).is_dir() or not any((licenses / name).iterdir()):
            raise ValueError(f"Declared notice directory is empty: {name}")
    return sha256(manifest_path)


def validate_output(output: Path) -> None:
    if output.name != IMAGE_NAME:
        raise ValueError(f"QA image name is fixed to {IMAGE_NAME}")
    for path in (output, output.with_name(SHA_NAME), output.with_name(PROVENANCE_NAME)):
        if path.exists() or path.is_symlink():
            raise ValueError("QA image output or evidence already exists")
    if output.resolve().is_relative_to(SOURCE_ROOT):
        raise ValueError("QA image output must be outside the source tree")


def stage(app: Path, staging: Path) -> Path:
    link = staging / APPLICATIONS_LINK
    link.symlink_to(APPLICATIONS_TARGET)
    staged_app = staging / APP_NAME
    shutil.copytree(app, staged_app, symlinks=True)
    inside = staged_app.resolve()
    for path in staging.rglob("*"):
        if not path.is_symlink() or path == link:
            continue
        if not path.resolve().is_relative_to(inside):
            raise ValueError(f"Staging symlink escapes the staged app: {path}")
    return staged_app


def run_hdiutil(command: list[str]) -> None:
    subprocess.run(command, check=True)


def create_image(staging: Path, output: Path, runner) -> None:
    hdiutil = ["/usr/bin/hdiutil"]
    runner([*hdiutil, "create", "-srcfolder", str(staging), "-volname", VOLUME_NAME, "-format", "UDZO", str(output)])
    if not output.is_file():
        raise ValueError("hdiutil did not produce the QA image")
    runner([*hdiutil, "verify", str(output)])


def remove_artifacts(output: Path) -> None:
    """Drop the image and both evidence sidecars, tolerating ones never written."""
    for path in (output, output.with_name(SHA_NAME), output.with_name(PROVENANCE_NAME)):
        path.unlink(missing_ok=True)


def write_evidence(output: Path, source_sha256: str, manifest_sha256: str) -> str:
    digest = sha256(output)
    output.with_name(SHA_NAME).write_text(f"{digest}  {IMAGE_NAME}\n")
    record = {
        "app": APP_NAME,
        "source_sha256": source_sha256,
        "manifest_sha256": manifest_sha256,
        "image_sha256": digest,
        "volume": VOLUME_NAME,
        "manifest_inventory_stage": "post-final-signing",
        "qa_only": True,
        "clearance": CLEARANCE,
        "byte_reproducibility": "not claimed; UDZO image bytes are not reproducible",
    }
    output.with_name(PROVENANCE_NAME).write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return digest


def package(app: Path, expected_source_sha256: str, output: Path, runner=run_hdiutil) -> str:
    manifest_sha256 = validate_source(app, expected_source_sha256)
    validate_output(output)
    with tempfile.TemporaryDirectory(prefix="xfinaudio-qa-") as staging:
        stage(app, Path(staging))
        try:
            create_image(Path(staging), output, runner)
        except Exception:
            remove_artifacts(output)
            raise
    try:
        return write_evidence(output, expected_source_sha256, manifest_sha256)
    except Exception:
        remove_artifacts(output)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--expected-source-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(package(args.app, args.expected_source_sha256, args.output))


if __name__ == "__main__":
    main()
