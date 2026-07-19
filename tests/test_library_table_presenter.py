from xfinaudio.desktop.library_table_presenter import sort_key_for_column, sort_rows_for_column
from xfinaudio.desktop.library_view_model import TrackDisplayRow


def _row(*, title: str = "Title", bpm: str = "120") -> TrackDisplayRow:
    return TrackDisplayRow(
        title=title,
        artist="Artist",
        bpm=bpm,
        musical_key="8A",
        energy="5",
        duration="3:20",
        spectral_color="GREEN",
        missing_fields="",
        genre="House",
        metadata_status="complete",
        path=f"/{title}.mp3",
        display_path=f"{title}.mp3",
    )


def test_sort_key_for_column_normalizes_titles() -> None:
    assert sort_key_for_column(_row(title="zETA"), 0) == "zeta"


def test_sort_key_for_column_places_missing_bpm_last() -> None:
    assert sort_key_for_column(_row(bpm="—"), 2) == float("inf")


def test_missing_numeric_values_stay_last_in_both_sort_directions() -> None:
    rows = [_row(title="missing", bpm="—"), _row(title="slow", bpm="100"), _row(title="fast", bpm="130")]

    assert [row.title for row in sort_rows_for_column(rows, 2, ascending=True)] == ["slow", "fast", "missing"]
    assert [row.title for row in sort_rows_for_column(rows, 2, ascending=False)] == ["fast", "slow", "missing"]
