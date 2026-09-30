"""Layout tests for the Metadata Worklist screen."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.screens.metadata_screen import MetadataScreen
from xfinaudio.library.models import TrackRecord


def test_worklist_table_uses_the_free_vertical_space(qapp: QApplication) -> None:
    """A trailing addStretch(1) competed with the table for the free height.

    Measured at 1200x660: the table got 172px, about five visible rows, or 26%
    of the screen, while the spacer below it took the rest.

    The empty-state label shares the same stretch factor, so it is hidden here
    to measure the state that actually matters -- a scanned library.
    """
    screen = MetadataScreen()
    screen.resize(1200, 660)
    screen.show()
    screen.worklist_empty_label.hide()
    qapp.processEvents()

    table = screen.worklist_table
    row_height = max(table.verticalHeader().defaultSectionSize(), 1)

    assert table.viewport().height() // row_height >= 10
    assert table.height() > 0.5 * screen.height()


# ----------------------------------------------------------------------
# Idempotent render + selection restore (render-contract-hardening T2)
# ----------------------------------------------------------------------


def _record(path: str) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=path,
        artist="Test Artist",
        bpm=128.0,
        camelot_key="8A",
        energy_level=7,
        metadata_status="complete",
    )


def _render_worklist(screen: MetadataScreen, paths: list[str]) -> AppState:
    """Render the screen from a state whose scanned records are exactly *paths*."""
    state = AppState(scanned_records=[_record(path) for path in paths])
    screen.render(state)
    screen.status_combo.setCurrentText("All")
    screen.render(state)
    return state


def test_worklist_selection_survives_same_rows_render(qapp: QApplication) -> None:
    """A second render with unchanged rows must not wipe the worklist selection.

    render() runs on every state sync while the Metadata tab is visible, and the
    destructive setRowCount(0) rebuild cleared the selection each time even when
    the rows were identical.
    """
    screen = MetadataScreen()
    _render_worklist(screen, ["/music/a.mp3", "/music/b.mp3"])

    table = screen.worklist_table
    table.selectRow(1)
    assert table.currentRow() == 1

    _render_worklist(screen, ["/music/a.mp3", "/music/b.mp3"])

    assert table.rowCount() == 2
    assert table.currentRow() == 1
    assert table.item(1, 0).isSelected()


def test_worklist_selection_restored_by_path_when_rows_change(qapp: QApplication) -> None:
    """When rows change, the selection follows the track path, not the row index."""
    screen = MetadataScreen()
    _render_worklist(screen, ["/music/a.mp3", "/music/b.mp3", "/music/c.mp3"])

    table = screen.worklist_table
    table.selectRow(1)  # /music/b.mp3

    _render_worklist(screen, ["/music/c.mp3", "/music/a.mp3", "/music/b.mp3"])

    assert table.currentRow() == 2
    assert table.item(table.currentRow(), 0).data(Qt.ItemDataRole.UserRole) == "/music/b.mp3"
    assert table.item(table.currentRow(), 0).isSelected()


def test_worklist_table_updates_when_rows_change(qapp: QApplication) -> None:
    """The signature cache must not freeze the worklist: changed rows still rebuild it."""
    screen = MetadataScreen()
    _render_worklist(screen, ["/music/a.mp3", "/music/b.mp3"])
    _render_worklist(screen, ["/music/c.mp3"])

    table = screen.worklist_table
    assert table.rowCount() == 1
    assert table.item(0, 0).data(Qt.ItemDataRole.UserRole) == "/music/c.mp3"


# ----------------------------------------------------------------------
# Gap summary row (MIK enrichment slice C)
# ----------------------------------------------------------------------


def _incomplete_record(path: str) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=path,
        artist="Test Artist",
        bpm=None,
        camelot_key=None,
        energy_level=None,
        metadata_status="incomplete",
    )


def test_gap_summary_label_is_height_capped_and_sits_above_the_filters(qapp: QApplication) -> None:
    """A new row may not eat the worklist height: it is capped and placed above the filters."""
    screen = MetadataScreen()
    screen.resize(1200, 660)
    screen.show()
    qapp.processEvents()

    label = screen.gap_summary_label
    assert 0 < label.maximumHeight() <= 32
    assert label.y() < screen.status_combo.y()


def test_gap_summary_label_renders_counts_from_scanned_records(qapp: QApplication) -> None:
    screen = MetadataScreen()
    state = AppState(scanned_records=[_incomplete_record("/music/gap.flac")])

    screen.render(state)

    text = screen.gap_summary_label.text()
    assert "BPM: 1" in text
    assert "Key: 1" in text
    assert "Energy: 1" in text
    assert screen.gap_summary_label.isVisibleTo(screen) is True


def test_gap_summary_label_hides_without_scanned_records(qapp: QApplication) -> None:
    screen = MetadataScreen()

    screen.render(AppState())

    assert screen.gap_summary_label.isVisibleTo(screen) is False


def test_gap_export_button_has_tooltip_and_accessible_name(qapp: QApplication) -> None:
    screen = MetadataScreen()

    assert screen.gap_export_button.toolTip().strip()
    assert screen.gap_export_button.accessibleName().strip()


def test_gap_export_button_emits_the_export_signal(qapp: QApplication) -> None:
    screen = MetadataScreen()
    screen.gap_export_button.setEnabled(True)
    emitted: list[bool] = []
    screen.gap_report_export_requested.connect(lambda: emitted.append(True))

    screen.gap_export_button.click()

    assert emitted == [True]


def test_gap_export_button_enabled_follows_state_gaps(qapp: QApplication) -> None:
    screen = MetadataScreen()

    screen.render(AppState(scanned_records=[_record("/music/complete.flac")]))
    assert screen.gap_export_button.isEnabled() is False

    screen.render(AppState(scanned_records=[_incomplete_record("/music/gap.flac")]))
    assert screen.gap_export_button.isEnabled() is True
