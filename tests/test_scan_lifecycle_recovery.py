"""Visible scan completion and recoverable watcher startup regression tests."""

from types import SimpleNamespace

import pytest

from xfinaudio.desktop.main_window import MainWindow


class _Scan:
    def scan(self, folder, **kwargs):
        return []


class _Repository:
    def save_scan_results(self, records, **kwargs):
        pass


@pytest.mark.parametrize("watch_fails", [False, True])
def test_completed_scan_publishes_clean_state_even_if_watch_unavailable(qapp, tmp_path, monkeypatch, watch_fails):
    window = MainWindow(scan_service=_Scan(), repository=_Repository())
    monkeypatch.setattr(window._library_controller, "start_spectral_completion_worker", lambda records: None)
    window.set_selected_folder(tmp_path)
    # This exercises scan cleanup, not watcher delivery: establish the dirty
    # precondition without invoking a timeout from an unarmed watch.
    window._replace_app_state(window._state.model_copy(update={"changes_detected_since_scan": True}))
    window._sync_state()
    assert window._state.changes_detected_since_scan
    if watch_fails:

        def fail(*args):
            raise FileNotFoundError("folder disappeared")

        monkeypatch.setattr(window._library_watch_service._folder_watcher, "start", fail)
    window._scan_service.begin_scan_state()
    window._scan_service.on_completed(
        SimpleNamespace(cancelled=False, records=[], complete_count=0, incomplete_count=0)
    )
    window._sync_state()
    assert window.current_scan_cancellation_token is None
    assert not window._state.changes_detected_since_scan
    assert window._library_controller._state is window._state
    assert window._library_watch_service._state is window._state
    assert window._scan_service._state is window._state
    assert window._library_screen.rescan_button.isHidden()
    assert window._library_screen.scan_button.isEnabled()
    if watch_fails:
        assert not window._library_watch_service.is_watching
        assert "watch" in window.status_label.text().lower()
    window.close()


def test_close_survives_geometry_save_failure(qapp, monkeypatch, caplog):
    from xfinaudio.config.settings_repository import SettingsRepositoryError

    window = MainWindow(scan_service=_Scan(), repository=_Repository())

    def fail():
        raise SettingsRepositoryError("disk full")

    monkeypatch.setattr(window, "_persist_window_geometry", fail)
    from PySide6.QtGui import QCloseEvent

    event = QCloseEvent()
    window.closeEvent(event)
    assert event.isAccepted()
    assert "settings" in caplog.text.lower()


def test_replacement_scan_cancels_only_previous_token(monkeypatch):
    from unittest.mock import Mock

    from xfinaudio.desktop.scan_service import ScanService
    from xfinaudio.library.scan_service import ScanCancellationToken

    service = ScanService(Mock())
    service._scan_thread = Mock()
    previous, replacement = ScanCancellationToken(), ScanCancellationToken()
    service._current_token = previous
    service.current_scan_cancellation_token = replacement
    monkeypatch.setattr(service, "_start_scan_worker", lambda *args: None)
    from pathlib import Path

    service.start_scan(Path("/synthetic"), replacement)
    assert previous.is_cancelled
    assert not replacement.is_cancelled
