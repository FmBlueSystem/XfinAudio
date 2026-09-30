"""Visible scan completion and recoverable watcher startup regression tests."""

from types import SimpleNamespace

import pytest

from xfinaudio.desktop.main_window import MainWindow


@pytest.mark.parametrize("watch_fails", [False, True])
def test_completed_scan_publishes_clean_state_even_if_watch_unavailable(qapp, tmp_path, monkeypatch, watch_fails):
    window = MainWindow(scan_service=SimpleNamespace(), repository=SimpleNamespace())
    monkeypatch.setattr(window._library_controller, "start_spectral_completion_worker", lambda records: None)
    window.set_selected_folder(tmp_path)
    window._library_watch_service._on_settle_timeout()
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
