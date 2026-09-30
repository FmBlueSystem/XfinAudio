"""Real Library widgets: interpret, edit, invalid retry and clear without network."""

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.library_view_model import LibraryViewModel
from xfinaudio.desktop.screens.library_screen import LibraryScreen
from xfinaudio.library.models import TrackRecord


def screen_with_tracks(qapp):
    screen = LibraryScreen()
    records = [
        TrackRecord(path="a", genre="House", bpm=124, camelot_key="8A", energy_level=6),
        TrackRecord(path="b", genre="House", bpm=130, camelot_key="8A", energy_level=6),
        TrackRecord(path="c", genre="House", bpm=None),
    ]
    screen.render(LibraryViewModel(), AppState(scanned_records=records))
    return screen


def visible_count(screen):
    return sum(not screen.tracks_table.isRowHidden(i) for i in range(screen.tracks_table.rowCount()))


def test_interpret_edit_clear_widgets(qapp):
    screen = screen_with_tracks(qapp)
    panel = screen.query_panel
    QTest.keyClicks(panel.request_input, "House bpm 120-128 key 8A energy 4-7")
    QTest.mouseClick(panel.interpret_button, Qt.MouseButton.LeftButton)
    assert panel.fields["genre"].text() == "House"
    assert panel.fields["bpm_max"].text() == "128"
    assert visible_count(screen) == 1
    panel.fields["bpm_max"].setText("132")
    QTest.mouseClick(panel.apply_button, Qt.MouseButton.LeftButton)
    assert visible_count(screen) == 2
    QTest.mouseClick(panel.clear_button, Qt.MouseButton.LeftButton)
    assert visible_count(screen) == 3
    screen.close()


def test_invalid_edit_retains_applied_filters_and_retry_works(qapp):
    screen = screen_with_tracks(qapp)
    panel = screen.query_panel
    panel.request_input.setText("bpm 120-128")
    panel.interpret_button.click()
    panel.fields["bpm_max"].setText("100")
    panel.apply_button.click()
    assert "minimum" in panel.status.text()
    assert visible_count(screen) == 1
    panel.fields["bpm_max"].setText("135")
    panel.apply_button.click()
    assert visible_count(screen) == 2
    panel.request_input.setText("happy music with invented key")
    panel.interpret_button.click()
    assert "unsupported" in panel.status.text()
    assert visible_count(screen) == 2
    screen.close()


def test_main_window_filter_callback_preserves_described_filters(qapp, monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    from tests.test_main_window import FakeRepository, FakeScanService
    from xfinaudio.desktop.main_window import MainWindow

    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    records = [TrackRecord(path="a", title="Song", bpm=124), TrackRecord(path="b", title="Song", bpm=130)]
    window.scanned_records = records
    window._records_by_path = {record.path: record for record in records}
    screen = window._library_screen
    screen.render(window._library_vm, window._state)
    screen.query_panel.request_input.setText("bpm 120-128")
    screen.query_panel.interpret_button.click()
    assert visible_count(screen) == 1
    screen.search_input.setText("Song")
    window._apply_song_filter()
    assert visible_count(screen) == 1
    window.close()
