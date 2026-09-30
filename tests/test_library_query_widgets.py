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
