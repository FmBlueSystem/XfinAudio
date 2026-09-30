"""Keyboard-visible deterministic Review explanations, using synthetic metadata."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPlainTextEdit

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.desktop.recommendation_render import show_transition_review
from xfinaudio.desktop.review_view_model import ReviewViewModel
from xfinaudio.desktop.screens.review_screen import ReviewScreen
from xfinaudio.exporting.explainability import PlaylistExplanation, TrackExplanation, TransitionExplanation
from xfinaudio.library.models import TrackRecord


def _explanation(prefix: str = "", *, warnings: bool = True) -> PlaylistExplanation:
    tracks = [
        TrackExplanation(path=f"/synthetic/{prefix}{name}.flac", title=f"{prefix}{name}", metadata_status="complete")
        for name in ("Opening", "Middle", "Closing")
    ]
    return PlaylistExplanation(
        strategy="harmonic_journey",
        optimizer="test",
        track_count=3,
        transition_count=2,
        total_score=0.8,
        warnings=[],
        transitions=[
            TransitionExplanation(
                order=index + 1,
                left=tracks[index],
                right=tracks[index + 1],
                component_scores={"harmonic": 0.9, "bpm": 0.8, "energy": 0.7, "tags": 0.6},
                compatibility_score=0.85,
                mixability_score=0.75,
                final_score=0.8,
                warnings=["BPM jump 6.2% exceeds threshold"] if warnings else [],
                explanations=["Harmonic neighbor", "BPM difference 6.2%", "Energy rises one level"],
            )
            for index in range(2)
        ],
    )


def _screen(qapp: QApplication) -> ReviewScreen:
    screen = ReviewScreen()
    screen.resize(1000, 700)
    show_transition_review(review_screen=screen, explanation=_explanation())
    screen.show()
    qapp.processEvents()
    return screen


def test_keyboard_navigation_exposes_context_warnings_and_current_score(qapp: QApplication) -> None:
    screen = _screen(qapp)
    table = screen.transition_table
    table.setFocus()
    table.setCurrentCell(0, 3)
    details = screen.findChild(QPlainTextEdit, "transition_details")
    assert details is not None, "Review needs a visible selectable explanation area"
    assert details.isVisible()
    assert "Opening" in details.toPlainText() and "Middle" in details.toPlainText()
    assert "BPM jump 6.2%" in details.toPlainText()
    assert table.item(0, 3).toolTip() in details.toPlainText()

    QTest.keyClick(table, Qt.Key.Key_Right)
    assert "BPM: 0.800" in details.toPlainText()
    assert table.item(0, 4).toolTip() in details.toPlainText()
    assert "Harmonic neighbor" not in details.toPlainText()
    QTest.keyClick(table, Qt.Key.Key_Down)
    assert "Closing" in details.toPlainText()
    assert "Opening" not in details.toPlainText()
    screen.close()


@pytest.mark.parametrize("column", [0, 1, 2, 5, 6, 7, 8, 9, 10])
def test_selected_rows_and_remaining_scores_have_relevant_explanations(qapp: QApplication, column: int) -> None:
    screen = _screen(qapp)
    screen.transition_table.setCurrentCell(0, column)
    details = screen.findChild(QPlainTextEdit, "transition_details")
    assert details is not None
    score_column = column if 3 <= column <= 9 else 9
    assert screen.transition_table.item(0, score_column).toolTip() in details.toPlainText()
    screen.close()


def test_details_are_read_only_selectable_and_in_keyboard_order(qapp: QApplication) -> None:
    screen = _screen(qapp)
    table = screen.transition_table
    table.setCurrentCell(0, 3)
    table.setFocus()
    details = screen.findChild(QPlainTextEdit, "transition_details")
    assert details is not None
    assert details.isReadOnly()
    assert details.accessibleName()
    assert "select" in screen.transition_help_label.text().lower()
    QTest.keyClick(table, Qt.Key.Key_Tab)
    assert details.hasFocus()
    before = details.toPlainText()
    QTest.keyClick(details, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    assert details.textCursor().selectedText()
    QTest.keyClicks(details, "cannot edit")
    assert details.toPlainText() == before
    QTest.keyClick(details, Qt.Key.Key_Tab)
    assert screen.readiness_table.hasFocus()
    screen.close()


def test_unchanged_render_preserves_current_cell_details_and_text_selection(qapp: QApplication) -> None:
    screen = _screen(qapp)
    screen.transition_table.setCurrentCell(1, 4)
    details = screen.findChild(QPlainTextEdit, "transition_details")
    assert details is not None
    details.selectAll()
    before = details.toPlainText()
    selected = details.textCursor().selectedText()
    screen.render(ReviewViewModel(), AppState())
    show_transition_review(review_screen=screen, explanation=_explanation())
    assert screen.transition_table.currentRow() == 1
    assert screen.transition_table.currentColumn() == 4
    assert details.toPlainText() == before
    assert details.textCursor().selectedText() == selected
    screen.close()


@pytest.mark.parametrize("change", ["clear_rows", "clear_contents", "deselect", "replace"])
def test_clearing_or_replacing_transition_context_removes_stale_details(qapp: QApplication, change: str) -> None:
    screen = _screen(qapp)
    table = screen.transition_table
    table.setCurrentCell(0, 3)
    details = screen.findChild(QPlainTextEdit, "transition_details")
    assert details is not None
    assert "Opening" in details.toPlainText()
    if change == "clear_rows":
        table.setRowCount(0)
    elif change == "clear_contents":
        table.clearContents()
    elif change == "deselect":
        table.clearSelection()
    else:
        show_transition_review(review_screen=screen, explanation=_explanation("Replacement "))
    assert details.toPlainText() == ""
    assert not details.isVisible()
    screen.close()


def test_score_and_warning_refresh_do_not_keep_previous_explanations(qapp: QApplication) -> None:
    screen = _screen(qapp)
    table = screen.transition_table
    table.setCurrentCell(0, 4)
    details = screen.findChild(QPlainTextEdit, "transition_details")
    assert details is not None
    table.item(0, 4).setToolTip("Updated tempo explanation")
    table.item(0, 10).setToolTip("")
    table.item(0, 10).setText("")
    assert "Updated tempo explanation" in details.toPlainText()
    assert "No warnings" in details.toPlainText()
    assert "BPM jump" not in details.toPlainText()
    screen.close()


def test_long_explanations_can_be_scrolled_by_keyboard(qapp: QApplication) -> None:
    screen = _screen(qapp)
    screen.transition_table.item(0, 9).setToolTip("\n".join(f"Reason {index}" for index in range(50)))
    screen.transition_table.setCurrentCell(0, 9)
    details = screen.findChild(QPlainTextEdit, "transition_details")
    assert details is not None
    details.setFocus()
    qapp.processEvents()
    assert details.verticalScrollBar().maximum() > 0
    QTest.keyClick(details, Qt.Key.Key_End, Qt.KeyboardModifier.ControlModifier)
    assert details.verticalScrollBar().value() > 0
    assert details.textCursor().atEnd()
    assert details.viewport().rect().contains(details.cursorRect())
    assert "Reason 49" in details.toPlainText()
    screen.close()


def test_generated_applied_review_keeps_details_and_navigation_reachable_at_1000_by_700(
    qapp: QApplication, tmp_path: Path
) -> None:
    window = MainWindow.with_defaults(tmp_path / "db.sqlite3", tmp_path / "settings.json")
    try:
        window.show_tracks(
            [
                TrackRecord(
                    path=f"/synthetic/{index}.flac",
                    title=f"Synthetic {index}",
                    bpm=120 + index,
                    camelot_key="8A",
                    energy_level=5,
                    metadata_status="complete",
                )
                for index in range(3)
            ]
        )
        window._on_library_selection_changed(["/synthetic/0.flac"])
        window.generate_prep_copilot()
        deadline = time.monotonic() + 5
        while (
            window._state.is_preparing_copilot or window._prep_task._thread is not None
        ) and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.005)
        assert not window._state.is_preparing_copilot
        assert window._prep_task._thread is None
        window._build_screen.apply_variant_button.click()
        window.workflow_tabs.setCurrentIndex(2)
        screen = window._review_screen
        assert screen.transition_table.rowCount() > 0
        screen.transition_table.setCurrentCell(0, 3)
        details = screen.findChild(QPlainTextEdit, "transition_details")
        assert details is not None
        window.resize(1000, 700)
        window.show()
        qapp.processEvents()
        window.resize(1000, 700)
        qapp.processEvents()
        assert window.width() <= 1000 and window.height() <= 700
        for widget in (details, screen.back_button, screen.export_button, screen.save_to_playlists_button):
            assert widget.isVisible()
            assert window.rect().contains(widget.mapTo(window, QPoint(0, 0)))
            assert window.rect().contains(widget.mapTo(window, widget.rect().bottomRight()))
        assert (
            screen.transition_table.viewport().height() >= screen.transition_table.verticalHeader().defaultSectionSize()
        )
    finally:
        window.close()
