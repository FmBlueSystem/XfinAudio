"""Package install smoke check tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "package_install_smoke.py"

ENTRY_POINTS_TXT = "[console_scripts]\nxfinaudio = xfinaudio.desktop.app:main\n"


def load_package_install_smoke():
    """Load the package install smoke script module."""
    assert SCRIPT_PATH.exists(), "package install smoke script is missing"
    spec = importlib.util.spec_from_file_location("package_install_smoke", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_script_exposes_expected_entry_point() -> None:
    module = load_package_install_smoke()

    assert module.EXPECTED_ENTRY_POINT == ("xfinaudio", "xfinaudio.desktop.app:main")


def test_parse_console_scripts_reads_only_console_scripts_section() -> None:
    module = load_package_install_smoke()
    text = "[gui_scripts]\nother = pkg:main\n\n" + ENTRY_POINTS_TXT

    assert module.parse_console_scripts(text) == {"xfinaudio": "xfinaudio.desktop.app:main"}


def test_verify_entry_points_passes_for_correct_console_script() -> None:
    module = load_package_install_smoke()

    module.verify_entry_points(ENTRY_POINTS_TXT)


def test_verify_entry_points_rejects_missing_console_script() -> None:
    module = load_package_install_smoke()

    with pytest.raises(module.PackageInstallSmokeError, match="xfinaudio"):
        module.verify_entry_points("[console_scripts]\nother = pkg:main\n")


def test_verify_entry_points_rejects_wrong_target() -> None:
    module = load_package_install_smoke()

    with pytest.raises(module.PackageInstallSmokeError, match="xfinaudio.desktop.app:main"):
        module.verify_entry_points("[console_scripts]\nxfinaudio = wrong.module:main\n")


def test_run_install_smoke_uses_temp_dirs_and_rejects_root_build_dist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_package_install_smoke()
    project_root = tmp_path / "project"
    project_root.mkdir()
    commands: list[list[str]] = []

    def fake_run(command: list[str], cwd: Path | None = None, check: bool = True) -> object:
        commands.append(command)
        if command[:2] == ["uv", "build"]:
            out_dir = Path(command[command.index("--out-dir") + 1])
            assert out_dir != project_root / "dist"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "xfinaudio-0.1.0-py3-none-any.whl").write_bytes(b"wheel")
        return object()

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(module, "verify_installed_entry_points", lambda venv_dir: None)

    module.run_install_smoke(project_root)

    assert commands[0][:4] == ["uv", "build", "--wheel", "--out-dir"]
    assert any(command[1:3] == ["-m", "venv"] for command in commands)
