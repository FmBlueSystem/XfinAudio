from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from xfinaudio.desktop import app as desktop_app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = PROJECT_ROOT / "packaging" / "pyinstaller" / "xfinaudio.spec"
SMOKE_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "pyinstaller_build_smoke.py"
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"

_smoke_script_spec = importlib.util.spec_from_file_location("pyinstaller_build_smoke", SMOKE_SCRIPT_PATH)
assert _smoke_script_spec is not None
assert _smoke_script_spec.loader is not None
pyinstaller_build_smoke = importlib.util.module_from_spec(_smoke_script_spec)
_smoke_script_spec.loader.exec_module(pyinstaller_build_smoke)


def _gitignore_lines() -> list[str]:
    return [line.strip() for line in (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()]


def test_gitignore_ignores_pyinstaller_build_and_dist_artifacts_without_global_spec_ignore() -> None:
    lines = _gitignore_lines()

    assert "build/" in lines
    assert "dist/" in lines
    assert "*.spec" not in lines


def test_pyinstaller_is_pinned_in_dev_dependencies() -> None:
    pyproject_text = PYPROJECT_PATH.read_text(encoding="utf-8")

    assert "pyinstaller==6.20.0" in pyproject_text


def test_pyinstaller_spec_declares_safe_xfinaudio_desktop_bundle_configuration() -> None:
    assert SPEC_PATH.exists()

    spec_text = SPEC_PATH.read_text(encoding="utf-8")

    assert "src/xfinaudio/desktop/app.py" in spec_text
    assert "name='XfinAudio'" in spec_text or 'name="XfinAudio"' in spec_text
    assert "pathex=[str(project_root / 'src')]" in spec_text or 'pathex=[str(project_root / "src")]' in spec_text

    forbidden_fragments = (
        "Music/",
        "Serato",
        "_Serato_",
        "Path.home()",
        "~/",
        "/Users/",
        "Audio Library",
    )
    for fragment in forbidden_fragments:
        assert fragment not in spec_text


def test_pyinstaller_smoke_check_only_prints_version_and_spec_without_root_artifacts() -> None:
    assert not (PROJECT_ROOT / "build").exists()
    assert not (PROJECT_ROOT / "dist").exists()

    result = subprocess.run(
        [sys.executable, str(SMOKE_SCRIPT_PATH), "--check-only"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "PyInstaller version:" in result.stdout
    assert f"Spec path: {SPEC_PATH}" in result.stdout
    assert "Check-only mode; no build executed." in result.stdout
    assert not (PROJECT_ROOT / "build").exists()
    assert not (PROJECT_ROOT / "dist").exists()


def test_package_smoke_enabled_reads_explicit_environment_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XFINAUDIO_PACKAGE_SMOKE", raising=False)
    assert desktop_app.package_smoke_enabled() is False

    monkeypatch.setenv("XFINAUDIO_PACKAGE_SMOKE", "1")
    assert desktop_app.package_smoke_enabled() is True


def test_app_path_helpers_use_environment_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "smoke.sqlite3"
    settings_path = tmp_path / "settings.json"

    monkeypatch.setenv("XFINAUDIO_DB_PATH", str(db_path))
    monkeypatch.setenv("XFINAUDIO_SETTINGS_PATH", str(settings_path))

    assert desktop_app.database_path_from_environment() == db_path
    assert desktop_app.settings_path_from_environment() == settings_path


def test_desktop_main_exits_before_event_loop_in_package_smoke_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[str] = []
    db_path = tmp_path / "smoke.sqlite3"
    settings_path = tmp_path / "settings.json"

    class FakeApplication:
        def __init__(self, argv: list[str]) -> None:
            events.append("app")

        def setApplicationName(self, name: str) -> None:
            pass

        def setApplicationDisplayName(self, name: str) -> None:
            pass

        def exec(self) -> int:
            events.append("exec")
            return 1

    def fake_with_defaults(*_args: object) -> object:
        raise AssertionError("package smoke must not create MainWindow")

    monkeypatch.setenv("XFINAUDIO_PACKAGE_SMOKE", "1")
    monkeypatch.setenv("XFINAUDIO_DB_PATH", str(db_path))
    monkeypatch.setenv("XFINAUDIO_SETTINGS_PATH", str(settings_path))
    monkeypatch.setattr(desktop_app, "QApplication", FakeApplication)
    monkeypatch.setattr(desktop_app.MainWindow, "with_defaults", fake_with_defaults)

    assert desktop_app.main() == 0
    assert events == ["app"]


def test_validate_launch_requires_temp_build() -> None:
    with pytest.raises(SystemExit):
        pyinstaller_build_smoke.parse_args(["--validate-launch"])


def test_pyinstaller_smoke_script_documents_temp_launch_environment() -> None:
    script_text = SMOKE_SCRIPT_PATH.read_text(encoding="utf-8")

    assert "XFINAUDIO_PACKAGE_SMOKE" in script_text
    assert "XFINAUDIO_DB_PATH" in script_text
    assert "XFINAUDIO_SETTINGS_PATH" in script_text
    assert "temp_root" in script_text


def test_launch_validation_uses_temp_database_and_settings_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}
    executable = tmp_path / "dist" / "XfinAudio.app" / "Contents" / "MacOS" / "XfinAudio"
    executable.parent.mkdir(parents=True)
    executable.write_text("", encoding="utf-8")

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        timeout: int,
        capture_output: bool,
        text: bool,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["cwd"] = cwd
        captured["env"] = env
        captured["timeout"] = timeout
        captured["capture_output"] = capture_output
        captured["text"] = text
        captured["check"] = check
        return subprocess.CompletedProcess(command, 0, stdout="smoke ok", stderr="")

    monkeypatch.setattr(pyinstaller_build_smoke.subprocess, "run", fake_run)

    assert pyinstaller_build_smoke.validate_launch(tmp_path / "dist", tmp_path) == 0

    launch_env = captured["env"]
    assert captured["command"] == [str(executable)]
    assert isinstance(launch_env, dict)
    assert launch_env["XFINAUDIO_PACKAGE_SMOKE"] == "1"
    assert launch_env["XFINAUDIO_DB_PATH"] == str(tmp_path / "smoke" / "xfinaudio.sqlite3")
    assert launch_env["XFINAUDIO_SETTINGS_PATH"] == str(tmp_path / "smoke" / "settings.json")


def test_pyinstaller_smoke_script_documents_temp_build_paths() -> None:
    script_text = SMOKE_SCRIPT_PATH.read_text(encoding="utf-8")

    assert "--distpath" in script_text
    assert "--workpath" in script_text
    assert "--specpath" in script_text


def test_pyinstaller_warning_report_path_uses_work_directory_and_spec_stem(tmp_path: Path) -> None:
    warning_path = pyinstaller_build_smoke.warning_report_path_from_work_path(tmp_path / "build")

    assert warning_path == tmp_path / "build" / "xfinaudio" / "warn-xfinaudio.txt"


def test_parse_pyinstaller_warning_report_lines_ignores_header_and_non_warning_text() -> None:
    report_text = """
This file lists modules PyInstaller was not able to find.
Types if import:
 * top-level: imported at the top-level

missing module named org - imported by copy (optional)
INFO: checking Analysis
excluded module named _frozen_importlib - imported by importlib (optional)
"""

    warnings = pyinstaller_build_smoke.parse_warning_report_lines(report_text)

    assert warnings == [
        "missing module named org - imported by copy (optional)",
        "excluded module named _frozen_importlib - imported by importlib (optional)",
    ]


def test_triage_pyinstaller_warnings_allows_observed_optional_platform_and_dev_groups() -> None:
    warnings = [
        "missing module named _winapi - imported by encodings (delayed, conditional, optional)",
        "missing module named winreg - imported by platform (delayed, optional)",
        "missing module named org - imported by copy (optional)",
        "missing module named 'java.lang' - imported by platform (delayed, optional), "
        "xml.sax._exceptions (conditional)",
        "missing module named numpy - imported by pytest (delayed, optional)",
        "missing module named mypy - imported by pydantic.mypy (top-level)",
        "missing module named pydantic.BaseModel - imported by pydantic (conditional), "
        "xfinaudio.library.models (top-level)",
        "missing module named multiprocessing.get_context - imported by multiprocessing (top-level)",
        "missing module named annotationlib - imported by typing_extensions (conditional), "
        "pydantic.v1.main (delayed, conditional)",
        "excluded module named _frozen_importlib - imported by importlib (optional)",
    ]

    triage = pyinstaller_build_smoke.triage_warning_lines(warnings)

    assert triage.expected == warnings
    assert triage.unexpected == []


def test_triage_pyinstaller_warnings_surfaces_unknown_lines() -> None:
    unknown_warning = (
        "missing module named definitely_required_runtime_module - imported by xfinaudio.desktop.app (top-level)"
    )

    triage = pyinstaller_build_smoke.triage_warning_lines([unknown_warning])

    assert triage.expected == []
    assert triage.unexpected == [unknown_warning]


def test_run_temp_build_prints_warning_triage_after_successful_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    temp_root = tmp_path / "temp-build"
    work_path = temp_root / "build"
    warning_path = work_path / "xfinaudio" / "warn-xfinaudio.txt"

    def fake_run(command: list[str], *, cwd: Path, text: bool) -> subprocess.CompletedProcess[str]:
        assert command == ["pyinstaller", "xfinaudio.spec"]
        assert cwd == PROJECT_ROOT
        assert text is True
        warning_path.parent.mkdir(parents=True)
        warning_path.write_text(
            "missing module named _winapi - imported by encodings (delayed, conditional, optional)\n"
            "missing module named definitely_required_runtime_module - imported by xfinaudio.desktop.app (top-level)\n",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(pyinstaller_build_smoke, "_print_check_summary", lambda: None)
    monkeypatch.setattr(pyinstaller_build_smoke.tempfile, "mkdtemp", lambda prefix: str(temp_root))
    monkeypatch.setattr(
        pyinstaller_build_smoke, "_temp_build_command", lambda dist_path, work_path: ["pyinstaller", "xfinaudio.spec"]
    )
    monkeypatch.setattr(pyinstaller_build_smoke.subprocess, "run", fake_run)

    assert pyinstaller_build_smoke.run_temp_build() == 0

    output = capsys.readouterr().out
    assert f"PyInstaller warning report: {warning_path}" in output
    assert "PyInstaller expected warnings: 1" in output
    assert "PyInstaller unexpected warnings: 1" in output
    assert "definitely_required_runtime_module" in output
