"""Per-row loudness visibility in the library table."""

from __future__ import annotations

import pytest

from xfinaudio.audio.loudness import LoudnessProfile, LoudnessStatus
from xfinaudio.desktop.library_view_model import _to_display_row
from xfinaudio.desktop.theme import _TRACK_TABLE_COLUMN_WIDTHS
from xfinaudio.library.models import TrackRecord


def _profile(
    lufs: float | None = -9.8,
    *,
    status: LoudnessStatus = LoudnessStatus.MEASURED,
    lra: float | None = 4.2,
    dbtp: float | None = -1.4,
) -> LoudnessProfile:
    return LoudnessProfile(
        lufs_integrated=lufs,
        loudness_range_lra=lra,
        true_peak_dbtp=dbtp,
        status=status,
        engine_fingerprint="ffmpeg-test",
    )


def _record(profile: LoudnessProfile | None) -> TrackRecord:
    return TrackRecord(path="/library/track.flac", loudness_profile=profile)


def test_measured_profile_renders_a_one_decimal_lufs_value() -> None:
    assert _to_display_row(_record(_profile())).lufs == "-9.8"


@pytest.mark.parametrize(
    "profile",
    [
        None,
        _profile(None, status=LoudnessStatus.UNMEASURABLE, lra=None, dbtp=None),
        _profile(None, status=LoudnessStatus.TRANSIENT_FAILURE, lra=None, dbtp=None),
        _profile(None, status=LoudnessStatus.UNSUPPORTED, lra=None, dbtp=None),
        _profile(-14.0, status=LoudnessStatus.TOO_SHORT, lra=None, dbtp=None),
    ],
    ids=["not-measured", "unmeasurable", "transient", "unsupported", "too-short"],
)
def test_every_incomplete_state_renders_an_em_dash(profile: LoudnessProfile | None) -> None:
    """Only a complete measurement earns a number; everything else reads as absent."""
    assert _to_display_row(_record(profile)).lufs == "—"


def test_column_and_widths_contracts_stay_in_step() -> None:
    from xfinaudio.desktop.library_screen_rendering import _COLUMNS

    assert "LUFS" in _COLUMNS
    assert len(_TRACK_TABLE_COLUMN_WIDTHS) == len(_COLUMNS)


def test_every_hardcoded_column_index_tracks_the_column_order() -> None:
    """Four modules hardcode positions; inserting a column must not silently desync them."""
    from xfinaudio.desktop import layout, library_controller, library_screen_rendering, window_service_wiring
    from xfinaudio.desktop.library_screen_rendering import _COLUMNS
    from xfinaudio.desktop.screens import library_screen

    assert library_screen._COLUMNS == _COLUMNS
    assert _COLUMNS.index("Missing") == library_screen_rendering._MISSING_COLUMN
    assert _COLUMNS.index("Color") == library_controller._TRACK_COLOR_COLUMN
    for module in (layout, window_service_wiring):
        assert _COLUMNS.index("Title") == module._TRACK_TITLE_COLUMN
        assert _COLUMNS.index("Status") == module._TRACK_STATUS_COLUMN
    for module in (layout, window_service_wiring, library_controller):
        assert _COLUMNS.index("Path") == module._TRACK_PATH_COLUMN


def test_table_renders_the_lufs_value_in_its_own_column(qapp) -> None:
    from xfinaudio.desktop.library_screen_rendering import _COLUMNS
    from xfinaudio.desktop.screens.library_screen import LibraryScreen

    screen = LibraryScreen()
    screen._populate_table([_to_display_row(_record(_profile())), _to_display_row(_record(None))])

    column = _COLUMNS.index("LUFS")
    assert screen.tracks_table.item(0, column).text() == "-9.8"
    assert screen.tracks_table.item(1, column).text() == "—"


def test_sort_mapping_follows_the_column_names_not_stale_positions() -> None:
    """The sort mapping is a positional if-chain; pin it by name so an insert breaks loudly."""
    from xfinaudio.desktop.library_screen_rendering import _COLUMNS
    from xfinaudio.desktop.library_table_presenter import sort_key_for_column
    from xfinaudio.desktop.library_view_model import _to_display_row

    row = _to_display_row(
        TrackRecord(
            path="/library/z.flac",
            title="Zeta",
            artist="Artist",
            bpm=120.0,
            camelot_key="8A",
            energy_level=5,
            duration=200.0,
            genre="House",
            loudness_profile=_profile(),
        )
    )
    expected = {
        "Title": "zeta",
        "Artist": "artist",
        "BPM": 120.0,
        "Key": "8a",
        "Energy": 5,
        "LUFS": -9.8,
        "Duration": 200,
        "Genre": "house",
        "Path": "/library/z.flac",
    }
    for name, value in expected.items():
        assert sort_key_for_column(row, _COLUMNS.index(name)) == value, name


def test_unmeasured_rows_sort_last_in_both_directions() -> None:
    from xfinaudio.desktop.library_screen_rendering import _COLUMNS
    from xfinaudio.desktop.library_table_presenter import sort_rows_for_column
    from xfinaudio.desktop.library_view_model import _to_display_row

    measured = _to_display_row(_record(_profile()))
    unmeasured = _to_display_row(_record(None))
    column = _COLUMNS.index("LUFS")

    for ascending in (True, False):
        ordered = sort_rows_for_column([unmeasured, measured], column, ascending=ascending)
        assert ordered[-1] is unmeasured


def test_every_column_has_a_sort_key_and_a_width() -> None:
    """A column added without a sort key or a width must fail here, not render wrong."""
    from xfinaudio.desktop.library_columns import COLUMN_WIDTHS, COLUMNS
    from xfinaudio.desktop.library_table_presenter import _SORT_KEYS

    assert set(_SORT_KEYS) == set(COLUMNS)
    assert set(COLUMN_WIDTHS) == set(COLUMNS)


def test_a_row_missing_a_column_raises_instead_of_shifting() -> None:
    """ordered_cells is the guard that replaced hand-ordered positional lists."""
    from xfinaudio.desktop.library_columns import COLUMNS, ordered_cells

    complete = {name: name for name in COLUMNS}
    assert ordered_cells(complete) == list(COLUMNS)

    del complete["Genre"]
    with pytest.raises(KeyError, match="Genre"):
        ordered_cells(complete)
