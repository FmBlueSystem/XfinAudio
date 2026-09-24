"""Guard tests for the arc subset benchmark script.

The benchmark reads a library database, so it must refuse to touch the live
application database. A resolved-path comparison misses a hard link that reaches
the same inode from a different path, so the benchmark could read and mutate the
live library through it.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "arc_subset_benchmark.py"

_benchmark_spec = importlib.util.spec_from_file_location("arc_subset_benchmark", BENCHMARK_SCRIPT_PATH)
assert _benchmark_spec is not None
assert _benchmark_spec.loader is not None
arc_subset_benchmark = importlib.util.module_from_spec(_benchmark_spec)
_benchmark_spec.loader.exec_module(arc_subset_benchmark)


class _StubRepository:
    """Repository stand-in that never touches the database file."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def list_tracks(self) -> list[object]:
        return []


def test_main_refuses_a_hard_link_to_the_live_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "home"
    live = home / ".xfinaudio" / "xfinaudio.sqlite3"
    live.parent.mkdir(parents=True)
    live.write_bytes(b"stand-in for the live application database")
    hard_link = tmp_path / "scratch.sqlite3"
    os.link(live, hard_link)

    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setattr(arc_subset_benchmark, "TrackRepository", _StubRepository)

    assert arc_subset_benchmark.main(["--db", str(hard_link)]) == 2
    assert "refusing to read the live database" in capsys.readouterr().err
