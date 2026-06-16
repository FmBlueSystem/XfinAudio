"""Guards against import-order regressions between the quality and recommendation packages."""

from __future__ import annotations

import subprocess
import sys


def _import_in_fresh_interpreter(statement: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", statement],
        capture_output=True,
        text=True,
        check=False,
    )


def test_quality_can_be_imported_before_recommendation() -> None:
    # Importing the quality package first must not raise a circular ImportError via the
    # prep_copilot <-> dj_readiness cycle.
    result = _import_in_fresh_interpreter("import xfinaudio.quality.dj_readiness as m; print(m.DjReadinessReport)")
    assert result.returncode == 0, result.stderr


def test_quality_package_root_imports_clean_first() -> None:
    result = _import_in_fresh_interpreter("import xfinaudio.quality; print('ok')")
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
