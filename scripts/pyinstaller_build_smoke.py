#!/usr/bin/env python3
"""Run safe PyInstaller packaging checks for XfinAudio."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = PROJECT_ROOT / "packaging" / "pyinstaller" / "xfinaudio.spec"
WARNING_LINE_PREFIXES = ("missing module named ", "excluded module named ")
EXPECTED_WARNING_MODULES = {
    "_frozen_importlib",
    "_frozen_importlib_external",
    "_manylinux",
    "_overlapped",
    "_posixsubprocess",
    "_scproxy",
    "_typeshed",
    "_winapi",
    "_winreg",
    "annotationlib",
    "cython",
    "dotenv",
    "email_validator",
    "eval_type_backport",
    "grp",
    "hypothesis",
    "java",
    "msvcrt",
    "mypy",
    "nt",
    "org",
    "pydantic.BaseModel",
    "pydantic.PydanticSchemaGenerationError",
    "pydantic.PydanticUserError",
    "pyimod02_importers",
    "pwd",
    "resource",
    "rich",
    "rich.pretty",
    "sitecustomize",
    "toml",
    "usercustomize",
    "vms_lib",
    "winreg",
}
EXPECTED_WARNING_MODULE_PREFIXES = (
    "asyncio.",
    "distutils.",
    "java.",
    "multiprocessing.",
    "mypy.",
    "org.",
)
EXPECTED_OPTIONAL_DEV_IMPORTERS = {"IPython", "numpy", "pydantic", "pytest", "setuptools", "sphinx"}
_WARNING_MODULE_RE = re.compile(r"^(?:missing|excluded) module named (?P<module>\S+)")
_WARNING_IMPORTERS_RE = re.compile(r" - imported by (?P<importers>.*?)(?: \(|$)")


class WarningTriage(NamedTuple):
    """Expected and unexpected PyInstaller analysis warning lines."""

    expected: list[str]
    unexpected: list[str]


def _pyinstaller_executable() -> str:
    executable = shutil.which("pyinstaller")
    if executable is None:
        raise RuntimeError("pyinstaller executable was not found on PATH")
    return executable


def _pyinstaller_version() -> str:
    result = subprocess.run(
        [_pyinstaller_executable(), "--version"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _temp_build_command(dist_path: Path, work_path: Path) -> list[str]:
    return [
        _pyinstaller_executable(),
        "--noconfirm",
        "--clean",
        "--distpath",
        str(dist_path),
        "--workpath",
        str(work_path),
        str(SPEC_PATH),
    ]


def warning_report_path_from_work_path(work_path: Path) -> Path:
    """Return the PyInstaller analysis warning report path for a work directory."""
    spec_stem = SPEC_PATH.stem
    return work_path / spec_stem / f"warn-{spec_stem}.txt"


def parse_warning_report_lines(report_text: str) -> list[str]:
    """Extract warning lines from a PyInstaller analysis warning report."""
    return [line.strip() for line in report_text.splitlines() if line.strip().startswith(WARNING_LINE_PREFIXES)]


def _warning_module_name(warning_line: str) -> str | None:
    match = _WARNING_MODULE_RE.match(warning_line)
    if match is None:
        return None
    return match.group("module").strip("'\"")


def _warning_importers(warning_line: str) -> set[str]:
    match = _WARNING_IMPORTERS_RE.search(warning_line)
    if match is None:
        return set()
    return {importer.strip().split(".")[0] for importer in match.group("importers").split(",") if importer.strip()}


def _is_expected_warning(warning_line: str) -> bool:
    module_name = _warning_module_name(warning_line)
    if module_name in EXPECTED_WARNING_MODULES:
        return True
    if module_name is not None and module_name.startswith(EXPECTED_WARNING_MODULE_PREFIXES):
        return True
    return bool("optional" in warning_line and _warning_importers(warning_line) & EXPECTED_OPTIONAL_DEV_IMPORTERS)


def triage_warning_lines(warning_lines: list[str]) -> WarningTriage:
    """Split PyInstaller warning lines into conservative expected and unexpected groups."""
    expected: list[str] = []
    unexpected: list[str] = []
    for warning_line in warning_lines:
        if _is_expected_warning(warning_line):
            expected.append(warning_line)
        else:
            unexpected.append(warning_line)
    return WarningTriage(expected=expected, unexpected=unexpected)


def _read_warning_lines(warning_path: Path) -> list[str]:
    if not warning_path.exists():
        return []
    return parse_warning_report_lines(warning_path.read_text(encoding="utf-8"))


def _print_warning_triage(work_path: Path) -> WarningTriage:
    warning_path = warning_report_path_from_work_path(work_path)
    warning_lines = _read_warning_lines(warning_path)
    triage = triage_warning_lines(warning_lines)

    print(f"PyInstaller warning report: {warning_path}")
    print(f"PyInstaller expected warnings: {len(triage.expected)}")
    print(f"PyInstaller unexpected warnings: {len(triage.unexpected)}")
    if triage.unexpected:
        print("Unexpected PyInstaller warnings:")
        for warning_line in triage.unexpected:
            print(warning_line)
    return triage


def _print_check_summary() -> None:
    print(f"PyInstaller version: {_pyinstaller_version()}")
    print(f"Spec path: {SPEC_PATH}")


def run_check_only() -> int:
    """Print PyInstaller packaging metadata without building artifacts."""
    _print_check_summary()
    print("Check-only mode; no build executed.")
    print("Temp build command uses --distpath and --workpath under a temporary directory.")
    print("Spec generation remains explicit via the committed spec file; no root --specpath output is used.")
    return 0


def _built_executable(dist_path: Path) -> Path:
    """Return the built app executable path from a temporary PyInstaller dist directory."""
    app_executable = dist_path / "XfinAudio.app" / "Contents" / "MacOS" / "XfinAudio"
    if app_executable.exists():
        return app_executable

    onedir_executable = dist_path / "XfinAudio" / "XfinAudio"
    if onedir_executable.exists():
        return onedir_executable

    onefile_executable = dist_path / "XfinAudio"
    if onefile_executable.exists():
        return onefile_executable

    raise FileNotFoundError(f"Could not find built XfinAudio executable under {dist_path}")


def validate_launch(dist_path: Path, temp_root: Path, timeout_seconds: int = 20) -> int:
    """Launch the built app in package smoke mode with temp-only app data paths."""
    executable = _built_executable(dist_path)
    smoke_path = temp_root / "smoke"
    smoke_path.mkdir(parents=True, exist_ok=True)
    launch_env = os.environ.copy()
    launch_env.update(
        {
            "XFINAUDIO_PACKAGE_SMOKE": "1",
            "XFINAUDIO_DB_PATH": str(smoke_path / "xfinaudio.sqlite3"),
            "XFINAUDIO_SETTINGS_PATH": str(smoke_path / "settings.json"),
        }
    )

    print(f"Launch validation executable: {executable}")
    print(f"Launch validation DB path: {launch_env['XFINAUDIO_DB_PATH']}")
    print(f"Launch validation settings path: {launch_env['XFINAUDIO_SETTINGS_PATH']}")

    try:
        result = subprocess.run(
            [str(executable)],
            cwd=PROJECT_ROOT,
            env=launch_env,
            timeout=timeout_seconds,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        print(f"Launch validation timed out after {timeout_seconds} seconds", file=sys.stderr)
        return 124

    if result.stdout:
        print("Launch stdout:")
        print(result.stdout)
    if result.stderr:
        print("Launch stderr:")
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        print(f"Launch validation failed with exit code {result.returncode}", file=sys.stderr)
        return result.returncode

    print("Launch validation completed in package smoke mode.")
    return 0


def run_temp_build(validate_launch_after_build: bool = False) -> int:
    """Run PyInstaller with all build outputs directed to temporary directories."""
    _print_check_summary()

    temp_root = Path(tempfile.mkdtemp(prefix="xfinaudio-pyinstaller-"))
    dist_path = temp_root / "dist"
    work_path = temp_root / "build"
    command = _temp_build_command(dist_path, work_path)

    print(f"Temp root: {temp_root}")
    print(f"Temp dist path: {dist_path}")
    print(f"Temp work path: {work_path}")
    print("Build command:")
    print(" ".join(command))

    result = subprocess.run(command, cwd=PROJECT_ROOT, text=True)
    if result.returncode != 0:
        print(f"PyInstaller failed with exit code {result.returncode}", file=sys.stderr)
        return result.returncode

    print("PyInstaller temp build completed.")
    _print_warning_triage(work_path)
    if validate_launch_after_build:
        launch_result = validate_launch(dist_path, temp_root)
        if launch_result != 0:
            return launch_result
    print(f"Artifacts remain under: {temp_root}")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments for the packaging smoke script."""
    parser = argparse.ArgumentParser(description="Safely smoke-check the XfinAudio PyInstaller packaging spike.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check-only",
        action="store_true",
        help="Print PyInstaller version/spec details without building.",
    )
    mode.add_argument(
        "--build-temp",
        action="store_true",
        help="Run PyInstaller using temporary dist/build paths.",
    )
    parser.add_argument(
        "--validate-launch",
        action="store_true",
        help="After --build-temp, launch the built app in temp-only package smoke mode.",
    )
    args = parser.parse_args(argv)
    if args.validate_launch and not args.build_temp:
        parser.error("--validate-launch requires --build-temp")
    return args


def main(argv: list[str] | None = None) -> int:
    """Run check-only mode by default, or a temporary build when requested."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.build_temp:
        return run_temp_build(validate_launch_after_build=args.validate_launch)
    return run_check_only()


if __name__ == "__main__":
    raise SystemExit(main())
