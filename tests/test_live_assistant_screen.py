"""Tests for LiveAssistantScreen — Qt widget tests."""

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from xfinaudio.desktop.screens.live_assistant_screen import LiveAssistantScreen
from xfinaudio.library.models import TrackRecord


@pytest.fixture()
def track_a() -> TrackRecord:
    return TrackRecord(
        path="/a.flac",
        title="Track A",
        artist="Artist A",
        bpm=128.0,
        camelot_key="11B",
        energy_level=7,
        metadata_status="complete",
    )


@pytest.fixture()
def track_b() -> TrackRecord:
    return TrackRecord(
        path="/b.flac",
        title="Track B",
        artist="Artist B",
        bpm=129.0,
        camelot_key="12B",
        energy_level=7,
        metadata_status="complete",
    )


@pytest.fixture()
def track_c() -> TrackRecord:
    return TrackRecord(
        path="/c.flac",
        title="Track C",
        artist="Artist C",
        bpm=135.0,
        camelot_key="3A",
        energy_level=8,
        metadata_status="complete",
    )


def test_live_assistant_screen_constructs(qapp: QApplication) -> None:
    screen = LiveAssistantScreen()
    assert screen is not None
    assert screen.windowTitle() == "Live Assistant"


def test_set_current_track_updates_now_playing(qapp: QApplication, track_a: TrackRecord) -> None:
    screen = LiveAssistantScreen()
    screen.set_current_track(track_a)

    assert screen._now_playing_title.text() == "Track A"
    assert screen._now_playing_artist.text() == "Artist A"
    assert "128" in screen._now_playing_bpm.text()
    assert "11B" in screen._now_playing_key.text()
    assert "7" in screen._now_playing_energy.text()


def test_set_candidates_populates_suggestions(qapp: QApplication, track_a: TrackRecord, track_b: TrackRecord) -> None:
    screen = LiveAssistantScreen()
    screen.set_current_track(track_a)
    screen.set_candidates([track_b])

    assert screen._suggestion_rows[0]._title_label.text() == "Track B"


def test_suggestion_row_hidden_when_no_candidate(qapp: QApplication, track_a: TrackRecord) -> None:
    screen = LiveAssistantScreen()
    screen.set_current_track(track_a)
    screen.set_candidates([])

    assert screen._suggestion_rows[0].isVisible() is False
    assert screen._suggestion_rows[1].isVisible() is False
    assert screen._suggestion_rows[2].isVisible() is False


def test_load_next_emits_signal(qapp: QApplication, track_a: TrackRecord, track_b: TrackRecord) -> None:
    screen = LiveAssistantScreen()
    received: list[str] = []
    screen.load_next_requested.connect(lambda path: received.append(path))

    screen.set_current_track(track_a)
    screen.set_candidates([track_b])
    screen._suggestion_rows[0]._load_button.click()

    assert received == [track_b.path]


def test_preview_requested_emits_signal(qapp: QApplication, track_a: TrackRecord, track_b: TrackRecord) -> None:
    screen = LiveAssistantScreen()
    received: list[str] = []
    screen.preview_requested.connect(lambda path: received.append(path))

    screen.set_current_track(track_a)
    screen.set_candidates([track_b])
    screen._suggestion_rows[0]._preview_button.click()

    assert received == [track_b.path]


def test_exit_requested_emits_signal(qapp: QApplication) -> None:
    screen = LiveAssistantScreen()
    received: list[bool] = []
    screen.exit_requested.connect(lambda: received.append(True))

    screen._exit_button.click()

    assert received == [True]


def test_history_appends_on_load_next(qapp: QApplication, track_a: TrackRecord, track_b: TrackRecord) -> None:
    screen = LiveAssistantScreen()
    screen.set_current_track(track_a)
    screen.set_candidates([track_b])
    screen._suggestion_rows[0]._load_button.click()

    assert screen._history_table.rowCount() == 1
    assert screen._history_table.item(0, 1).text() == "Track A"


def test_empty_state_shows_when_no_current_track(qapp: QApplication) -> None:
    screen = LiveAssistantScreen()
    assert screen._empty_state_widget is not None
    assert screen._content_widget is not None


def test_guidance_banner_visible_without_current_track(qapp: QApplication) -> None:
    screen = LiveAssistantScreen()
    screen.show()
    qapp.processEvents()

    guidance_labels = screen.findChildren(QLabel, "guidanceLabel")

    assert len(guidance_labels) == 1
    guidance_text = guidance_labels[0].text()
    assert "Pick a track to start the session" in guidance_text
    assert "Preview candidates with the play button" in guidance_text
    assert "Load Next" in guidance_text
    assert "Space" in guidance_text
    assert "L" in guidance_text
    assert guidance_labels[0].wordWrap() is True
    assert guidance_labels[0].isVisible() is True


def test_content_shows_when_current_track_set(qapp: QApplication, track_a: TrackRecord) -> None:
    screen = LiveAssistantScreen()
    screen.set_current_track(track_a)
    assert screen._current_track == track_a


def test_guidance_banner_hides_when_current_track_set(qapp: QApplication, track_a: TrackRecord) -> None:
    screen = LiveAssistantScreen()
    screen.set_current_track(track_a)

    guidance_labels = screen.findChildren(QLabel, "guidanceLabel")

    assert len(guidance_labels) == 1
    assert guidance_labels[0].isVisible() is False


def test_keyboard_shortcut_esc_emits_exit(qapp: QApplication) -> None:
    screen = LiveAssistantScreen()
    received: list[bool] = []
    screen.exit_requested.connect(lambda: received.append(True))

    screen._shortcut_esc.activated.emit()

    assert received == [True]


def test_root_layout_has_consistent_margins(qapp: QApplication) -> None:
    """LiveAssistant aligns to the 12/8 margins used by every other screen."""
    screen = LiveAssistantScreen()
    margins = screen.layout().contentsMargins()
    assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (12, 12, 12, 12)
    assert screen.layout().spacing() == 8
