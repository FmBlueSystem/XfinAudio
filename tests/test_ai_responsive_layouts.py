"""Shown desktop geometry with synthetic metadata and isolated persistence."""

from __future__ import annotations

import socket
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QScrollArea, QWidget

from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.library.models import TrackRecord


def _settle(qapp: QApplication) -> None:
    for _ in range(8):
        qapp.processEvents()


def _inside(widget: QWidget, viewport: QWidget) -> bool:
    return viewport.rect().contains(widget.mapTo(viewport, QPoint())) and viewport.rect().contains(
        widget.mapTo(viewport, widget.rect().bottomRight())
    )


def _reachable(scroll: QScrollArea, widget: QWidget, qapp: QApplication) -> None:
    scroll.ensureWidgetVisible(widget)
    _settle(qapp)
    assert _inside(widget, scroll.viewport())


@pytest.fixture()
def desktop(qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[MainWindow]:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "0")
    for name in ("NAN_API_KEY", "XFINAUDIO_AI_ENV_FILE"):
        monkeypatch.delenv(name, raising=False)

    def no_network(*args: object, **kwargs: object) -> None:
        pytest.fail("Layout fixtures must not connect to a provider")

    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(socket.socket, "connect", no_network)
    window = MainWindow.with_defaults(tmp_path / "library.sqlite3", tmp_path / "settings.json")
    window.resize(1440, 1000)
    window.show()
    window.show_tracks(
        [
            TrackRecord(
                path=f"/synthetic/{index}.flac",
                title=f"Synthetic Dawn Circuit {index}",
                artist="Synthetic Atlas Ensemble",
                bpm=120 + index,
                camelot_key="8A",
                energy_level=5,
                genre="House",
                duration=240,
                metadata_status="complete",
            )
            for index in range(6)
        ]
    )
    window._library_screen.tracks_table.selectRow(0)
    _settle(qapp)
    try:
        yield window
    finally:
        window._playlist_editor.discard_draft()
        window.close()
        _settle(qapp)


@pytest.mark.parametrize("size", [(1000, 700), (1440, 1000)])
def test_library_expanded_filters_preserve_real_window_size(desktop: MainWindow, qapp: QApplication, size) -> None:
    screen = desktop._library_screen
    screen.query_panel.request_input.setText("House, BPM 120-128")
    screen.query_panel.interpret_button.click()
    screen.tracks_table.selectRow(0)
    desktop.resize(*size)
    _settle(qapp)
    assert (desktop.width(), desktop.height()) == size
    assert screen.loudness_detail_pane.isVisible()
    assert _inside(screen.proceed_button, desktop)
    assert screen.tracks_table.viewport().height() >= screen.tracks_table.verticalHeader().defaultSectionSize() * 3
    if size[0] == 1440:
        assert _inside(screen.folder_button, screen.controls_scroll.viewport())
        assert _inside(screen.clear_filters_button, screen.controls_scroll.viewport())
    _reachable(screen.controls_scroll, screen.query_panel.apply_button, qapp)
    _reachable(screen.controls_scroll, screen.clear_filters_button, qapp)


@pytest.mark.parametrize("size", [(1000, 700), (1440, 1000)])
def test_review_expanded_details_preserve_real_window_size(desktop: MainWindow, qapp: QApplication, size) -> None:
    desktop.generate_prep_copilot()
    deadline = time.monotonic() + 5
    while (
        desktop._state.is_preparing_copilot or desktop._prep_task._thread is not None
    ) and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.005)
    assert desktop._prep_task._thread is None
    desktop._build_screen.apply_variant_button.click()
    desktop.workflow_tabs.setCurrentIndex(2)
    screen = desktop._review_screen
    screen.engine_facts_button.click()
    screen.recommendation_table.selectRow(1)
    screen.compare_replacement_button.click()
    screen.transition_table.setCurrentCell(0, 3)
    desktop.resize(*size)
    _settle(qapp)
    assert (desktop.width(), desktop.height()) == size
    assert _inside(screen.back_button, desktop)
    assert _inside(screen.export_button, desktop)
    for widget in (screen.engine_facts_details, screen.replacement_details, screen.transition_details):
        assert widget.isVisible()
        _reachable(screen.content_scroll, widget, qapp)
    _reachable(screen.content_scroll, screen.configure_ai_button, qapp)


def _wait_for_copilot(desktop: MainWindow, qapp: QApplication) -> None:
    deadline = time.monotonic() + 5
    while (
        desktop._state.is_asking_copilot or desktop._ai_copilot._copilot_thread is not None
    ) and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.005)
    assert desktop._ai_copilot._copilot_thread is None
    _settle(qapp)


@pytest.mark.parametrize("size", [(1000, 700), (1440, 1000)])
def test_create_recovery_uses_space_and_is_visible(desktop: MainWindow, qapp: QApplication, size) -> None:
    desktop.workflow_tabs.setCurrentIndex(1)
    desktop.resize(*size)
    screen = desktop._build_screen
    screen.copilot_ask_input.setText("Build a House set")
    screen.copilot_ask_button.click()
    _wait_for_copilot(desktop, qapp)
    assert "Configure AI" in screen.copilot_ask_status.text()
    assert (desktop.width(), desktop.height()) == size
    assert _inside(screen.copilot_ask_status, screen.controls_scroll.viewport())
    assert _inside(screen.copilot_configure_button, screen.controls_scroll.viewport())
    assert _inside(screen.proceed_button, desktop)
    if size[0] == 1440:
        assert screen.controls_scroll.height() > 500


@pytest.mark.parametrize("size", [(1000, 700), (1440, 1000)])
def test_create_confirmation_is_revealed_without_forcing_window_size(
    desktop: MainWindow, qapp: QApplication, size, monkeypatch: pytest.MonkeyPatch
) -> None:
    from xfinaudio.recommendation.prep_copilot import DJSetIntent

    monkeypatch.setattr(
        desktop._ai_copilot,
        "_intent_extractor",
        lambda *args, **kwargs: DJSetIntent(name="Synthetic House", target_track_count=6, genre_focus="House"),
    )
    desktop.workflow_tabs.setCurrentIndex(1)
    desktop.resize(*size)
    screen = desktop._build_screen
    screen.copilot_ask_input.setText("Build a House set")
    screen.copilot_ask_button.click()
    _wait_for_copilot(desktop, qapp)
    assert screen.intent_preview.isVisible()
    assert (desktop.width(), desktop.height()) == size
    assert _inside(screen.intent_preview.confirm_button, screen.controls_scroll.viewport())
    assert _inside(screen.intent_preview.edit_button, screen.controls_scroll.viewport())
    screen.controls_scroll.verticalScrollBar().setValue(0)
    desktop._sync_state()
    _settle(qapp)
    assert screen.controls_scroll.verticalScrollBar().value() == 0


@pytest.mark.parametrize("size", [(1000, 700), (1440, 1000)])
def test_editor_actions_fit_styled_button_labels(desktop: MainWindow, qapp: QApplication, size) -> None:
    playlist = desktop._playlist_repository.create("Synthetic set", [r.path for r in desktop._state.scanned_records])
    assert playlist.id is not None
    desktop._playlist_coordinator.open_playlist(playlist.id)
    desktop.resize(*size)
    _settle(qapp)
    table = desktop._playlist_editor.tracks_table
    button = table.cellWidget(0, 4)
    assert button is not None
    assert button.width() >= button.sizeHint().width()
    assert button.height() >= button.sizeHint().height()
    assert button.toolTip()
    assert _inside(button, table.viewport())
    assert table.columnWidth(4) >= button.sizeHint().width()
    assert (desktop.width(), desktop.height()) == size


@pytest.mark.parametrize("size", [(1000, 700), (1440, 1000)])
def test_live_history_shares_spare_width_between_track_names(desktop: MainWindow, qapp: QApplication, size) -> None:
    screen = desktop._live_assistant_screen
    track = desktop._state.scanned_records[0]
    desktop.workflow_tabs.setTabEnabled(6, True)
    desktop.workflow_tabs.setCurrentIndex(6)
    screen.set_current_track(track)
    screen.append_history(track)
    desktop.resize(*size)
    _settle(qapp)
    table = screen._history_table
    header = table.horizontalHeader()
    assert table.columnWidth(1) > table.columnWidth(3) * 2
    assert table.columnWidth(2) > table.columnWidth(3) * 2
    assert abs(header.length() - table.viewport().width()) <= 2
    assert (desktop.width(), desktop.height()) == size
