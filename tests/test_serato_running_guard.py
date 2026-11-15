"""No crate is written while Serato DJ runs (S13).

Serato keeps its crates in memory and rewrites its `_Serato_` folder when it
quits, so a crate written while it runs is deleted on exit. A confirmed export
therefore refuses while Serato DJ Pro or Lite is open, writes nothing, and keeps
the preview so the user can close Serato and confirm again.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import pytest

from tests.test_headless_backend import tagged_flac
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.common import BackendError
from xfinaudio.headless.serato_process import SERATO_PROCESS_NAMES, serato_is_running


def _fixture(tmp_path: Path) -> tuple[HeadlessBackend, dict[str, object], Path]:
    music = tmp_path / "music"
    for index in range(3):
        tagged_flac(music / f"{index}.flac", index)
    serato = tmp_path / "_Serato_"
    subcrates = serato / "Subcrates"
    subcrates.mkdir(parents=True)
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(music)})
    review = backend.execute("prep.generate", {"targetTrackCount": 2})
    destination = backend.execute("serato.registerDestination", {"seratoRoot": str(serato)})
    preview = backend.execute(
        "serato.preview",
        {"source": {"kind": "review", "reviewId": review["reviewId"]}, "destinationId": destination["destinationId"]},
    )
    return backend, preview, subcrates


def _commit(backend: HeadlessBackend, preview: dict[str, object]) -> dict[str, object]:
    return backend.execute("serato.commit", {"previewId": preview["previewId"], "confirmed": True})


def _listing(subcrates: Path) -> list[str]:
    return sorted(path.name for path in subcrates.iterdir())


def test_a_commit_while_serato_runs_writes_nothing_and_names_the_cause(tmp_path: Path) -> None:
    backend, preview, subcrates = _fixture(tmp_path)
    backend.serato.serato_running = lambda: True
    before = _listing(subcrates)

    with pytest.raises(BackendError) as failure:
        _commit(backend, preview)

    assert failure.value.code == "serato_running"
    assert str(failure.value) == "Close Serato DJ before exporting; it rewrites its crates when it quits"
    assert _listing(subcrates) == before == []


def test_the_same_preview_exports_once_serato_is_closed(tmp_path: Path) -> None:
    backend, preview, subcrates = _fixture(tmp_path)
    backend.serato.serato_running = lambda: True
    with pytest.raises(BackendError):
        _commit(backend, preview)

    backend.serato.serato_running = lambda: False
    receipt = _commit(backend, preview)

    assert receipt["parentsCreated"] == ["XfinAudio"]
    assert _listing(subcrates) == sorted(["XfinAudio.crate", str(receipt["filename"])])


def test_a_preview_is_still_allowed_while_serato_runs(tmp_path: Path) -> None:
    backend, preview, _subcrates = _fixture(tmp_path)
    backend.serato.serato_running = lambda: True

    summary = backend.execute("serato.confirmation", {"previewId": preview["previewId"]})

    assert summary["previewId"] == preview["previewId"]


def _completed(returncode: int) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout="", stderr="")


def test_macos_detection_asks_pgrep_for_each_exact_serato_name() -> None:
    calls: list[list[str]] = []

    def runner(args: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return _completed(0 if args[-1] == "Serato DJ Lite" else 1)

    assert serato_is_running(platform="darwin", runner=runner) is True
    assert calls == [["pgrep", "-x", "Serato DJ Pro"], ["pgrep", "-x", "Serato DJ Lite"]]
    assert SERATO_PROCESS_NAMES == ("Serato DJ Pro", "Serato DJ Lite")


def test_macos_detection_is_false_when_no_serato_process_exists() -> None:
    assert serato_is_running(platform="darwin", runner=lambda args: _completed(1)) is False


def test_windows_detection_reads_tasklist_for_the_exe_names() -> None:
    def runner(args: list[str]) -> subprocess.CompletedProcess[str]:
        found = args[-1] == "IMAGENAME eq Serato DJ Pro.exe"
        output = '"Serato DJ Pro.exe","4242"' if found else "INFO: No tasks are running"
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=output, stderr="")

    assert serato_is_running(platform="win32", runner=runner) is True
    assert serato_is_running(platform="win32", runner=lambda args: _completed(0)) is False


def test_a_detection_that_cannot_run_lets_the_export_through_with_a_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def missing(args: list[str]) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError(args[0])

    with caplog.at_level(logging.WARNING, logger="xfinaudio.headless.serato_process"):
        assert serato_is_running(platform="darwin", runner=missing) is False

    assert "could not check whether Serato DJ is running" in caplog.text
