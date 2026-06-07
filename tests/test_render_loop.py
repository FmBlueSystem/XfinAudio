"""Tests for the render loop: _sync_state feeds all screens via _render_screens."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.library.models import TrackRecord


def _ensure_app() -> QApplication:
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        return existing
    return QApplication([])


class _FakeScanService:
    def scan(self, folder: Path, **kwargs) -> list[TrackRecord]:
        return []


class _FakeRepository:
    def save_scan_results(self, records: list[TrackRecord]) -> None:
        pass


def _make_window() -> MainWindow:
    _ensure_app()
    return MainWindow(scan_service=_FakeScanService(), repository=_FakeRepository())


def _make_track(path: str) -> TrackRecord:
    return TrackRecord(
        path=path,
        title="Test",
        artist="Artist",
        bpm=120.0,
        camelot_key="8A",
        energy_level=6,
        metadata_status="complete",
    )


@pytest.fixture()
def qapp():
    return _ensure_app()


@pytest.fixture()
def window(qapp):
    return _make_window()


# ---------------------------------------------------------------------------
# Test 1: _render_screens does not raise with empty state
# ---------------------------------------------------------------------------


def test_render_screens_does_not_raise_with_empty_state(window: MainWindow) -> None:
    """_render_screens must be safe to call with a fully empty AppState."""
    window._render_screens()  # no exception expected


# ---------------------------------------------------------------------------
# Test 2: _render_screens does not raise with populated state
# ---------------------------------------------------------------------------


def test_render_screens_does_not_raise_with_full_state(window: MainWindow) -> None:
    """_render_screens must be safe after tracks are loaded and state is synced."""
    window.scanned_records = [_make_track("/music/a.flac")]
    window._sync_state()
    window._render_screens()  # no exception expected


# ---------------------------------------------------------------------------
# Test 3: _sync_state calls _render_screens
# ---------------------------------------------------------------------------


def test_sync_state_calls_render_screens(window: MainWindow, monkeypatch: pytest.MonkeyPatch) -> None:
    """_sync_state must invoke _render_screens exactly once per call."""
    called: list[bool] = []
    monkeypatch.setattr(window, "_render_screens", lambda: called.append(True))
    window._sync_state()
    assert len(called) == 1
