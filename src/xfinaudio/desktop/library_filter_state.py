"""Pure filter-state helpers for the library screen."""

from xfinaudio.desktop.library_view_model import LibraryFilters


def library_filters_from_flags(
    *,
    complete: bool = False,
    incomplete: bool = False,
    missing_bpm: bool = False,
    missing_key: bool = False,
    missing_energy: bool = False,
) -> LibraryFilters:
    status = "complete" if complete else "incomplete" if incomplete else None
    missing = "bpm" if missing_bpm else "camelot_key" if missing_key else "energy_level" if missing_energy else None
    return LibraryFilters(status_filter=status, missing_field_filter=missing)


def row_matches_query(values: tuple[str, ...], query: str) -> bool:
    normalized = query.strip().casefold()
    return not normalized or any(normalized in value.casefold() for value in values)
