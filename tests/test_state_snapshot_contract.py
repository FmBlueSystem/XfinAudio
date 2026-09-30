"""Snapshots do not change underneath renderers, services or undo consumers."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.library.scan_service import MetadataScanService, ScanProgress
from xfinaudio.library.track_repository import TrackRepository


def test_state_rejects_direct_field_mutation() -> None:
    state = AppState()
    with pytest.raises(FrozenInstanceError):
        state.is_scanning = True  # type: ignore[misc]


def test_model_copy_rejects_unknown_fields() -> None:
    state = AppState()
    with pytest.raises(TypeError):
        state.model_copy(update={"is_scaning": True})
    assert state.is_scanning is False


def test_shell_and_scan_publish_new_snapshots(qapp: QApplication, tmp_path: Path) -> None:
    window = MainWindow(scan_service=MetadataScanService(), repository=TrackRepository(tmp_path / "db"))
    original = window._state
    window.selected_folder = tmp_path
    assert original.selected_folder is None
    assert window._state.selected_folder == tmp_path
    before_scan = window._state
    window._begin_scan_state()
    assert before_scan.is_scanning is False
    started = window._state
    window._scan_service.on_progress(ScanProgress(1, 3, tmp_path / "synthetic.flac"))
    current = window._state
    assert started.scan_progress_count == 0
    assert current.scan_progress_count == 1
    assert current is window._app_controller._state
    assert current is window._library_controller._state
    assert current is window._scan_service._state
    assert current is window._recommendation_service._state
    window.close()
    qapp.processEvents()


def test_refresh_runtime_fields_keeps_old_snapshot(qapp: QApplication, tmp_path: Path) -> None:
    window = MainWindow(scan_service=MetadataScanService(), repository=TrackRepository(tmp_path / "db"))
    original = window._state
    window._library_selected_paths = ["/synthetic.flac"]
    window._refresh_state_fields()
    assert original.selected_library_paths == []
    assert window._state.selected_library_paths == ["/synthetic.flac"]
    assert window._app_controller._state is window._state
    window.close()
    qapp.processEvents()
