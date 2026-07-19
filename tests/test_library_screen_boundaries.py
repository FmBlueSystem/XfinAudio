from xfinaudio.desktop.library_filter_state import library_filters_from_flags, row_matches_query
from xfinaudio.desktop.library_screen_builder import build_library_screen_ui
from xfinaudio.desktop.library_view_model import LibraryFilters


def test_library_filters_from_flags_selects_status_and_missing_field() -> None:
    assert library_filters_from_flags(incomplete=True, missing_key=True) == LibraryFilters(
        status_filter="incomplete", missing_field_filter="camelot_key"
    )


def test_library_filters_from_flags_defaults_to_unfiltered() -> None:
    assert library_filters_from_flags() == LibraryFilters()


def test_row_matches_query_searches_visible_metadata() -> None:
    assert row_matches_query(("Track", "Artist", "128", "8A", "House"), "artist")
    assert not row_matches_query(("Track", "Artist", "128", "8A", "House"), "techno")


def test_library_builder_owns_complete_widget_construction(qapp) -> None:
    from xfinaudio.desktop.screens.library_screen import LibraryScreen

    screen = LibraryScreen()
    assert callable(build_library_screen_ui)
    assert screen.folder_button.text() == "Choose Folder"
    assert screen.tracks_table.columnCount() == 12
