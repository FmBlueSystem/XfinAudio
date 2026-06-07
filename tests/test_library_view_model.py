"""Tests for LibraryViewModel — library screen data transformation."""

from pathlib import Path

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.library_view_model import LibraryFilters, LibraryViewModel
from xfinaudio.library.models import TrackRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_track(
    path: str = "/library/track.mp3",
    title: str | None = "Test Track",
    artist: str | None = "Test Artist",
    bpm: float | None = 128.0,
    camelot_key: str | None = "8A",
    energy_level: int | None = 7,
    genre: str | None = "House",
    metadata_status: str = "complete",
    missing_required_fields: list[str] | None = None,
) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=title,
        artist=artist,
        bpm=bpm,
        camelot_key=camelot_key,
        energy_level=energy_level,
        genre=genre,
        metadata_status=metadata_status,  # type: ignore[arg-type]
        missing_required_fields=missing_required_fields or [],
    )


def make_state(
    tracks: list[TrackRecord] | None = None,
    folder: str | None = None,
    is_scanning: bool = False,
) -> AppState:
    state = AppState()
    if folder is not None:
        state.selected_folder = Path(folder)
    if tracks is not None:
        state = state.with_scanned_records(tracks)
    state.is_scanning = is_scanning
    return state


vm = LibraryViewModel()


# ---------------------------------------------------------------------------
# tracks_for_display — filtering
# ---------------------------------------------------------------------------


def test_tracks_for_display_no_filters_returns_all_tracks() -> None:
    tracks = [make_track(path="/lib/a.mp3"), make_track(path="/lib/b.mp3")]
    state = make_state(tracks=tracks)

    rows = vm.tracks_for_display(state)

    assert len(rows) == 2


def test_tracks_for_display_search_query_filters_by_title() -> None:
    tracks = [
        make_track(path="/lib/a.mp3", title="Deep House Anthem"),
        make_track(path="/lib/b.mp3", title="Techno Banger"),
    ]
    state = make_state(tracks=tracks)

    rows = vm.tracks_for_display(state, LibraryFilters(search_query="deep"))

    assert len(rows) == 1
    assert rows[0].title == "Deep House Anthem"


def test_tracks_for_display_status_filter_complete_returns_only_complete() -> None:
    tracks = [
        make_track(path="/lib/a.mp3", metadata_status="complete"),
        make_track(path="/lib/b.mp3", metadata_status="incomplete"),
    ]
    state = make_state(tracks=tracks)

    rows = vm.tracks_for_display(state, LibraryFilters(status_filter="complete"))

    assert len(rows) == 1
    assert rows[0].metadata_status == "complete"


def test_tracks_for_display_status_filter_incomplete_returns_only_incomplete() -> None:
    tracks = [
        make_track(path="/lib/a.mp3", metadata_status="complete"),
        make_track(path="/lib/b.mp3", metadata_status="incomplete"),
    ]
    state = make_state(tracks=tracks)

    rows = vm.tracks_for_display(state, LibraryFilters(status_filter="incomplete"))

    assert len(rows) == 1
    assert rows[0].metadata_status == "incomplete"


def test_tracks_for_display_missing_field_filter_returns_matching_tracks() -> None:
    tracks = [
        make_track(path="/lib/a.mp3", missing_required_fields=["bpm", "energy_level"]),
        make_track(path="/lib/b.mp3", missing_required_fields=[]),
    ]
    state = make_state(tracks=tracks)

    rows = vm.tracks_for_display(state, LibraryFilters(missing_field_filter="bpm"))

    assert len(rows) == 1
    assert rows[0].path == "/lib/a.mp3"


# ---------------------------------------------------------------------------
# tracks_for_display — field formatting
# ---------------------------------------------------------------------------


def test_bpm_none_formats_as_dash() -> None:
    state = make_state(tracks=[make_track(bpm=None)])

    rows = vm.tracks_for_display(state)

    assert rows[0].bpm == "—"


def test_bpm_value_formats_as_integer_string() -> None:
    state = make_state(tracks=[make_track(bpm=128.7)])

    rows = vm.tracks_for_display(state)

    assert rows[0].bpm == "128"


def test_energy_none_formats_as_dash() -> None:
    state = make_state(tracks=[make_track(energy_level=None)])

    rows = vm.tracks_for_display(state)

    assert rows[0].energy == "—"


def test_musical_key_empty_formats_as_dash() -> None:
    state = make_state(tracks=[make_track(camelot_key=None)])

    rows = vm.tracks_for_display(state)

    assert rows[0].musical_key == "—"


def test_musical_key_blank_string_formats_as_dash() -> None:
    state = make_state(tracks=[make_track(camelot_key="")])

    rows = vm.tracks_for_display(state)

    assert rows[0].musical_key == "—"


def test_display_path_is_filename_only() -> None:
    state = make_state(tracks=[make_track(path="/some/deep/folder/track.mp3")])

    rows = vm.tracks_for_display(state)

    assert rows[0].display_path == "track.mp3"


def test_missing_fields_with_values_joined_by_comma() -> None:
    state = make_state(
        tracks=[make_track(missing_required_fields=["bpm", "energy_level"])]
    )

    rows = vm.tracks_for_display(state)

    assert rows[0].missing_fields == "bpm, energy_level"


def test_missing_fields_empty_formats_as_dash() -> None:
    state = make_state(tracks=[make_track(missing_required_fields=[])])

    rows = vm.tracks_for_display(state)

    assert rows[0].missing_fields == "—"


# ---------------------------------------------------------------------------
# scan_button_enabled
# ---------------------------------------------------------------------------


def test_scan_button_enabled_with_folder_and_not_scanning() -> None:
    state = make_state(folder="/music", is_scanning=False)

    assert vm.scan_button_enabled(state) is True


def test_scan_button_enabled_false_without_folder() -> None:
    state = make_state(folder=None, is_scanning=False)

    assert vm.scan_button_enabled(state) is False


def test_scan_button_enabled_false_when_scanning() -> None:
    state = make_state(folder="/music", is_scanning=True)

    assert vm.scan_button_enabled(state) is False


# ---------------------------------------------------------------------------
# cancel_button_visible
# ---------------------------------------------------------------------------


def test_cancel_button_visible_when_scanning() -> None:
    state = make_state(is_scanning=True)

    assert vm.cancel_button_visible(state) is True


def test_cancel_button_not_visible_when_not_scanning() -> None:
    state = make_state(is_scanning=False)

    assert vm.cancel_button_visible(state) is False


# ---------------------------------------------------------------------------
# status_text
# ---------------------------------------------------------------------------


def test_status_text_no_folder() -> None:
    state = make_state()

    assert vm.status_text(state) == "Choose a folder to begin"


def test_status_text_folder_no_tracks_contains_ready_to_scan() -> None:
    state = make_state(folder="/music/collection")

    text = vm.status_text(state)

    assert "Ready to scan" in text
    assert "collection" in text


def test_status_text_scanning() -> None:
    state = make_state(folder="/music", is_scanning=True)

    assert vm.status_text(state) == "Scanning…"


def test_status_text_with_tracks_contains_count() -> None:
    tracks = [
        make_track(path="/lib/a.mp3", metadata_status="complete"),
        make_track(path="/lib/b.mp3", metadata_status="incomplete"),
    ]
    state = make_state(tracks=tracks, folder="/music")

    text = vm.status_text(state)

    assert "2" in text
    assert "1" in text  # 1 complete out of 2


# ---------------------------------------------------------------------------
# can_proceed
# ---------------------------------------------------------------------------


def test_can_proceed_without_tracks_is_false() -> None:
    state = make_state()

    assert vm.can_proceed(state) is False


def test_can_proceed_with_tracks_is_true() -> None:
    state = make_state(tracks=[make_track()])

    assert vm.can_proceed(state) is True


# ---------------------------------------------------------------------------
# selected_count_text
# ---------------------------------------------------------------------------


def test_selected_count_text_empty_list_returns_empty_string() -> None:
    assert vm.selected_count_text([]) == ""


def test_selected_count_text_one_item_returns_singular() -> None:
    assert vm.selected_count_text(["x"]) == "1 track selected"


def test_selected_count_text_multiple_items_returns_plural() -> None:
    assert vm.selected_count_text(["x", "y"]) == "2 tracks selected"
