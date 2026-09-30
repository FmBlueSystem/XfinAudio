"""Current-snapshot access publishes replacements and preserves a typed boundary."""

import json
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.state_access import AppStateAccess


def test_update_uses_current_snapshot_and_publishes_once() -> None:
    owner = [AppState()]
    published: list[AppState] = []

    def replace(state: AppState) -> None:
        published.append(state)
        owner[0] = state

    access = AppStateAccess(current=lambda: owner[0], replace=replace)
    owner[0] = owner[0].model_copy(update={"current_screen": "live"})
    original = owner[0]
    updated = access.update(is_scanning=True)

    assert updated is owner[0]
    assert published == [updated]
    assert updated.current_screen == "live"
    assert updated.is_scanning is True
    assert original.is_scanning is False


def test_unknown_update_does_not_publish_partial_state() -> None:
    original = AppState()
    published: list[AppState] = []
    access = AppStateAccess(current=lambda: original, replace=published.append)

    with pytest.raises(TypeError):
        access.update(is_scanning=True, is_scaning=True)

    assert published == []
    assert original.is_scanning is False


def test_type_checker_rejects_invalid_state_boundaries(tmp_path: Path) -> None:
    """Check real diagnostics so widening a callback to Any cannot silently pass."""
    source = dedent("""\
        from xfinaudio.desktop.app_state import AppState
        from xfinaudio.desktop.state_access import AppStateAccess

        state = AppState()
        def publish(value: AppState) -> None:
            pass
        def publish_text(value: str) -> None:
            pass
        access = AppStateAccess(current=lambda: state, replace=publish)
        access.replace(access.current().with_screen("live"))
        AppStateAccess(current=lambda: "invalid", replace=publish)  # error
        AppStateAccess(current=lambda: state, replace=publish_text)  # error
        access.replace("invalid")  # error
        state.is_scanning = True  # error
        state.with_screen("invalid")  # error
        """)
    fixture = tmp_path / "state_contract.py"
    fixture.write_text(source, encoding="utf-8")
    config = tmp_path / "pyrightconfig.json"
    config.write_text(
        json.dumps(
            {
                "include": [str(fixture)],
                "extraPaths": [str(Path(__file__).resolve().parents[1] / "src")],
                "typeCheckingMode": "basic",
                "pythonVersion": "3.12",
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "-m", "pyright", "--pythonpath", sys.executable, "--outputjson", "--project", str(config)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    report = json.loads(result.stdout)
    diagnostics = report["generalDiagnostics"]
    expected_lines = {index for index, line in enumerate(source.splitlines()) if "# error" in line}
    assert result.returncode == 1, result.stdout + result.stderr
    assert report["summary"]["errorCount"] == len(expected_lines), diagnostics
    assert {item["range"]["start"]["line"] for item in diagnostics} == expected_lines, diagnostics
    assert all(Path(item["file"]) == fixture for item in diagnostics), diagnostics
