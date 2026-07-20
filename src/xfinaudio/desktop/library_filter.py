"""Pure filtering functions for the track library — no Qt dependencies."""

from __future__ import annotations

from typing import NamedTuple

from xfinaudio.desktop.library_view_model import _DASH
from xfinaudio.library.duplicate_grouping import (
    duplicate_group_key,
    duplicate_representative_sort_key,
    normalize_artist_for_grouping,
    normalize_title_for_grouping,
)
from xfinaudio.library.models import TrackRecord


def metadata_status_records(records: list[TrackRecord], status: str) -> list[TrackRecord]:
    """Return records matching the requested metadata status."""
    return [r for r in records if r.metadata_status == status]


def metadata_missing_field_records(records: list[TrackRecord], missing_field: str) -> list[TrackRecord]:
    """Return incomplete records missing the requested metadata field."""
    return [r for r in records if r.metadata_status == "incomplete" and missing_field in r.missing_required_fields]


# ---------------------------------------------------------------------------
# Duplicate-version grouping — display-only, row-level filtering.
#
# The normalization/group-key/sort-key core lives in
# `xfinaudio.library.duplicate_grouping` (layer-neutral, Qt-free) — these are
# thin delegators only, so the Library screen display filter stays
# byte-identical while `recommendation/` can reuse the same core without
# depending on `desktop/`. See design.md Decision 3a.
# ---------------------------------------------------------------------------

_normalize_title_for_grouping = normalize_title_for_grouping
_normalize_artist_for_grouping = normalize_artist_for_grouping


def _duplicate_group_key(title: str | None, artist: str | None) -> tuple[str, str] | None:
    """Return the grouping key for *title*/*artist*, or None to force a singleton.

    None/blank/placeholder-dash title or artist is never grouped, since blank
    metadata tracks must never collapse into a fake "duplicate" group.
    """
    return duplicate_group_key(title, artist, placeholder=_DASH)


class _RowInfo(NamedTuple):
    """Rendered-row data needed for duplicate-group ranking — no TrackRecord dependency."""

    title: str
    artist: str
    status: str
    missing_field_count: int
    path: str


def _pick_duplicate_representative(rows: list[_RowInfo]) -> _RowInfo:
    """Pick the row to keep visible among a group of duplicate rows.

    Order: (1) complete status first, (2) lower missing-field count,
    (3) shortest original title, (4) alphabetical path as final tiebreak.
    """

    def sort_key(row: _RowInfo) -> tuple[int, int, int, str]:
        return duplicate_representative_sort_key(
            is_complete=row.status == "complete",
            missing_field_count=row.missing_field_count,
            title=row.title,
            path=row.path,
        )

    return min(rows, key=sort_key)


def suppressed_duplicate_paths(rows: list[_RowInfo]) -> set[str]:
    """Return the set of paths to hide, keeping one representative per duplicate group."""
    groups: dict[tuple[str, str], list[_RowInfo]] = {}
    for row in rows:
        key = _duplicate_group_key(row.title, row.artist)
        if key is None:
            continue
        groups.setdefault(key, []).append(row)

    suppressed: set[str] = set()
    for group_rows in groups.values():
        if len(group_rows) < 2:
            continue
        representative = _pick_duplicate_representative(group_rows)
        for row in group_rows:
            if row.path != representative.path:
                suppressed.add(row.path)
    return suppressed
