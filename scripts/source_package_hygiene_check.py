#!/usr/bin/env python3
"""Build and inspect source package artifacts for publication hygiene."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from email.parser import Parser
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RELEASE_GATE_COMMAND = ["uv", "build", "--out-dir", "<tempdir>"]
REQUIRED_SDIST_FILES = [
    "README.md",
    "LICENSE",
    "NOTICE.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "HARMONIC_MIXING.md",
    "pyproject.toml",
]
FORBIDDEN_FILE_NAMES = {"apiJira.txt", "context.md", ".DS_Store"}
FORBIDDEN_TOP_LEVEL_DIRS = {".release-evidence", "build", "dist"}


class SourcePackageHygieneError(RuntimeError):
    """Raised when source package hygiene validation fails."""


def _portable_members(member_names: list[str]) -> list[str]:
    """Normalize archive member names to portable slash-separated paths."""
    return [name.rstrip("/") for name in member_names if name and name != "/"]


def _strip_sdist_root(member_name: str) -> str:
    """Return the member path relative to the single sdist root directory."""
    parts = Path(member_name).parts
    if len(parts) < 2:
        return member_name
    return Path(*parts[1:]).as_posix()


def _relative_archive_paths(member_names: list[str], *, has_sdist_root: bool) -> set[str]:
    paths = set()
    for member_name in _portable_members(member_names):
        relative_name = _strip_sdist_root(member_name) if has_sdist_root else member_name
        if relative_name and relative_name != ".":
            paths.add(relative_name)
    return paths


def _forbidden_artifact_matches(relative_paths: set[str]) -> list[str]:
    """Return private/local archive paths that must not be published."""
    offenders: list[str] = []
    for relative_path in sorted(relative_paths):
        parts = Path(relative_path).parts
        if not parts:
            continue
        if any(part in FORBIDDEN_FILE_NAMES for part in parts):
            offenders.append(relative_path)
            continue
        if parts[0] in FORBIDDEN_TOP_LEVEL_DIRS:
            offenders.append(f"{parts[0]}/" if len(parts) == 1 else relative_path)
    return offenders


def _raise_if_forbidden(relative_paths: set[str], artifact_path: Path) -> None:
    offenders = _forbidden_artifact_matches(relative_paths)
    if offenders:
        offender_text = ", ".join(offenders)
        raise SourcePackageHygieneError(
            f"{artifact_path.name} contains forbidden publication artifacts: {offender_text}"
        )


def inspect_sdist(sdist_path: Path) -> dict[str, Any]:
    """Inspect an sdist tarball for forbidden files and required public docs."""
    with tarfile.open(sdist_path, "r:gz") as archive:
        relative_paths = _relative_archive_paths(archive.getnames(), has_sdist_root=True)

    _raise_if_forbidden(relative_paths, sdist_path)
    missing_docs = sorted(
        required_file for required_file in REQUIRED_SDIST_FILES if required_file not in relative_paths
    )
    if missing_docs:
        missing_text = ", ".join(missing_docs)
        raise SourcePackageHygieneError(f"{sdist_path.name} is missing required public source files: {missing_text}")
    return {"path": sdist_path, "required_files": REQUIRED_SDIST_FILES}


def _metadata_license(metadata: Any) -> str:
    return metadata.get("License-Expression") or metadata.get("License") or ""


def _metadata_has_readme_description(metadata: Any) -> bool:
    content_type = metadata.get("Description-Content-Type", "")
    payload = metadata.get_payload()
    return "text/markdown" in content_type.lower() and bool(str(payload).strip())


def inspect_wheel(wheel_path: Path) -> dict[str, Any]:
    """Inspect a wheel for forbidden files and public package metadata."""
    with zipfile.ZipFile(wheel_path) as archive:
        names = archive.namelist()
        relative_paths = _relative_archive_paths(names, has_sdist_root=False)
        metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
        if len(metadata_names) != 1:
            raise SourcePackageHygieneError(f"{wheel_path.name} must contain exactly one dist-info/METADATA file")
        metadata_text = archive.read(metadata_names[0]).decode("utf-8")

    _raise_if_forbidden(relative_paths, wheel_path)
    metadata = Parser().parsestr(metadata_text)
    license_text = _metadata_license(metadata)
    has_readme_description = _metadata_has_readme_description(metadata)
    if license_text != "GPL-3.0-only":
        raise SourcePackageHygieneError(f"{wheel_path.name} metadata does not declare GPL-3.0-only license")
    if not has_readme_description:
        raise SourcePackageHygieneError(
            f"{wheel_path.name} metadata does not include README-derived Markdown description"
        )
    return {"path": wheel_path, "license": license_text, "has_readme_description": has_readme_description}


def _root_artifact_offenders(project_root: Path) -> list[str]:
    return [name for name in ("build", "dist") if (project_root / name).exists()]


def assert_no_root_build_dist(project_root: Path) -> None:
    """Ensure project-root build/ and dist/ artifacts are absent."""
    offenders = _root_artifact_offenders(project_root)
    if offenders:
        offender_text = ", ".join(f"project-root {name}/" for name in offenders)
        raise SourcePackageHygieneError(f"Source package hygiene failed: {offender_text} present")


def _single_artifact(temp_dir: Path, pattern: str, label: str) -> Path:
    matches = sorted(temp_dir.glob(pattern))
    if len(matches) != 1:
        raise SourcePackageHygieneError(f"Expected exactly one {label} under {temp_dir}, found {len(matches)}")
    return matches[0]


def run_hygiene_check(project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Build source artifacts under a temporary directory and inspect them."""
    assert_no_root_build_dist(project_root)
    with tempfile.TemporaryDirectory(prefix="xfinaudio-source-package-") as temp_dir_name:
        temp_dir = Path(temp_dir_name).resolve()
        try:
            temp_dir.relative_to(project_root.resolve())
        except ValueError:
            pass
        else:
            raise SourcePackageHygieneError("Temporary build directory must be outside the project root")

        command = ["uv", "build", "--out-dir", str(temp_dir)]
        subprocess.run(command, cwd=project_root, check=True)
        sdist_path = _single_artifact(temp_dir, "*.tar.gz", "sdist")
        wheel_path = _single_artifact(temp_dir, "*.whl", "wheel")
        result = {"sdist": inspect_sdist(sdist_path), "wheel": inspect_wheel(wheel_path), "temp_dir": temp_dir}
        assert_no_root_build_dist(project_root)
        return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse source package hygiene check arguments."""
    parser = argparse.ArgumentParser(description="Build and verify XfinAudio source package hygiene.")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the source package hygiene check."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        result = run_hygiene_check(args.project_root)
    except (SourcePackageHygieneError, subprocess.CalledProcessError) as error:
        print(f"FAIL source package hygiene: {error}")
        return 1

    print(f"PASS source package hygiene: inspected {result['sdist']['path'].name} and {result['wheel']['path'].name}")
    print("PASS source package hygiene: project-root build/ and dist/ are absent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
