#!/usr/bin/env python3
"""Build the wheel and verify it installs and exposes the xfinaudio command."""

from __future__ import annotations

import argparse
import configparser
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ENTRY_POINT = ("xfinaudio", "xfinaudio.desktop.app:main")


class PackageInstallSmokeError(RuntimeError):
    """Raised when the package install smoke check fails."""


def parse_console_scripts(entry_points_text: str) -> dict[str, str]:
    """Return the [console_scripts] mapping from an entry_points.txt body."""
    parser = configparser.ConfigParser()
    parser.read_string(entry_points_text)
    if not parser.has_section("console_scripts"):
        return {}
    return dict(parser.items("console_scripts"))


def verify_entry_points(entry_points_text: str) -> None:
    """Verify the xfinaudio console script is registered with the right target."""
    name, target = EXPECTED_ENTRY_POINT
    console_scripts = parse_console_scripts(entry_points_text)
    if name not in console_scripts:
        raise PackageInstallSmokeError(f"installed package does not expose the '{name}' console script")
    actual = console_scripts[name].replace(" ", "")
    if actual != target:
        raise PackageInstallSmokeError(f"'{name}' console script targets '{actual}', expected '{target}'")


def _site_packages_dirs(venv_dir: Path) -> list[Path]:
    return sorted(venv_dir.glob("lib/python*/site-packages")) + sorted(venv_dir.glob("Lib/site-packages"))


def _entry_points_file(venv_dir: Path) -> Path:
    for site_packages in _site_packages_dirs(venv_dir):
        matches = sorted(site_packages.glob("xfinaudio-*.dist-info/entry_points.txt"))
        if matches:
            return matches[0]
    raise PackageInstallSmokeError("installed xfinaudio dist-info/entry_points.txt not found in venv")


def _entry_point_script(venv_dir: Path) -> Path:
    for candidate in (venv_dir / "bin" / "xfinaudio", venv_dir / "Scripts" / "xfinaudio.exe"):
        if candidate.exists():
            return candidate
    raise PackageInstallSmokeError("installed xfinaudio entry-point wrapper script not found in venv")


def verify_installed_entry_points(venv_dir: Path) -> None:
    """Verify the installed venv exposes the xfinaudio command and metadata."""
    _entry_point_script(venv_dir)
    verify_entry_points(_entry_points_file(venv_dir).read_text(encoding="utf-8"))


def _root_artifact_offenders(project_root: Path) -> list[str]:
    return [name for name in ("build", "dist") if (project_root / name).exists()]


def assert_no_root_build_dist(project_root: Path) -> None:
    """Ensure project-root build/ and dist/ artifacts are absent."""
    offenders = _root_artifact_offenders(project_root)
    if offenders:
        offender_text = ", ".join(f"project-root {name}/" for name in offenders)
        raise PackageInstallSmokeError(f"Package install smoke failed: {offender_text} present")


def _single_wheel(temp_dir: Path) -> Path:
    matches = sorted(temp_dir.glob("*.whl"))
    if len(matches) != 1:
        raise PackageInstallSmokeError(f"Expected exactly one wheel under {temp_dir}, found {len(matches)}")
    return matches[0]


def run_install_smoke(project_root: Path = PROJECT_ROOT) -> dict[str, Path]:
    """Build the wheel, install it into a temp venv, and verify the command."""
    assert_no_root_build_dist(project_root)
    with tempfile.TemporaryDirectory(prefix="xfinaudio-install-smoke-") as temp_dir_name:
        temp_dir = Path(temp_dir_name).resolve()
        try:
            temp_dir.relative_to(project_root.resolve())
        except ValueError:
            pass
        else:
            raise PackageInstallSmokeError("Temporary build directory must be outside the project root")

        dist_dir = temp_dir / "dist"
        venv_dir = temp_dir / "venv"
        subprocess.run(["uv", "build", "--wheel", "--out-dir", str(dist_dir)], cwd=project_root, check=True)
        wheel_path = _single_wheel(dist_dir)
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        venv_python = venv_dir / "bin" / "python"
        if not venv_python.exists():
            venv_python = venv_dir / "Scripts" / "python.exe"
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "--no-deps", "--quiet", str(wheel_path)],
            check=True,
        )
        verify_installed_entry_points(venv_dir)
        assert_no_root_build_dist(project_root)
        return {"wheel": wheel_path, "venv": venv_dir}


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse package install smoke arguments."""
    parser = argparse.ArgumentParser(description="Build and verify the XfinAudio wheel installs the xfinaudio command.")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the package install smoke check."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        result = run_install_smoke(args.project_root)
    except (PackageInstallSmokeError, subprocess.CalledProcessError) as error:
        print(f"FAIL package install smoke: {error}")
        return 1

    print(f"PASS package install smoke: installed {result['wheel'].name} and resolved the xfinaudio command")
    print("PASS package install smoke: project-root build/ and dist/ are absent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
