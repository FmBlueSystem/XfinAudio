"""Pure filtering functions for the track library — no Qt dependencies."""

from __future__ import annotations

import re
from typing import NamedTuple

from xfinaudio.desktop.library_view_model import _DASH
from xfinaudio.library.models import TrackRecord


def metadata_status_records(records: list[TrackRecord], status: str) -> list[TrackRecord]:
    """Return records matching the requested metadata status."""
    return [r for r in records if r.metadata_status == status]


def metadata_missing_field_records(records: list[TrackRecord], missing_field: str) -> list[TrackRecord]:
    """Return incomplete records missing the requested metadata field."""
    return [r for r in records if r.metadata_status == "incomplete" and missing_field in r.missing_required_fields]


# ---------------------------------------------------------------------------
# Duplicate-version grouping — display-only, row-level filtering.
# ---------------------------------------------------------------------------

# Trailing " - <CamelotKey> - Energy <N>" suffix, e.g. " - 12A - Energy 7".
# Camelot key anchored to the real shape: 1-12 followed by A or B (real-case text).
_CAMELOT_ENERGY_SUFFIX = re.compile(r"\s*-\s*(?:[1-9]|1[0-2])[AB]\s*-\s*Energy\s+\d+\s*$")

# Trailing "(vN)" version marker, e.g. "(v2)".
_VERSION_SUFFIX = re.compile(r"\s*\(v\d+\)\s*$")


def _normalize_title_for_grouping(title: str) -> str:
    """Strip app-generated technical suffixes, repeatedly, then casefold.

    Suffix stripping happens against the original-case text first (the regex is
    written for real-case text like "Energy"/"A"/"B") — casefolding happens last.
    Remix/edit/mix descriptor *content* is never touched, but the parentheses
    around it are stripped as punctuation: real-world exports are inconsistent
    about wrapping a descriptor in parens (e.g. "Song (Remix)" vs "Song Remix"
    for the exact same file), so treating "(" / ")" as opaque would fail to
    group those two forms of the same descriptor together — which defeats the
    whole point of this feature for exactly that case.
    """
    text = title.strip()
    changed = True
    while changed:
        changed = False
        stripped = _CAMELOT_ENERGY_SUFFIX.sub("", text)
        if stripped != text:
            text = stripped.strip()
            changed = True
            continue
        stripped = _VERSION_SUFFIX.sub("", text)
        if stripped != text:
            text = stripped.strip()
            changed = True
    text = text.replace("(", " ").replace(")", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text.casefold()


def _normalize_artist_for_grouping(artist: str) -> str:
    """Strip whitespace and casefold — no suffix stripping for artist names."""
    return artist.strip().casefold()


def _duplicate_group_key(title: str | None, artist: str | None) -> tuple[str, str] | None:
    """Return the grouping key for *title*/*artist*, or None to force a singleton.

    None/blank/placeholder-dash title or artist is never grouped, since blank
    metadata tracks must never collapse into a fake "duplicate" group.
    """
    if title is None or artist is None:
        return None
    title_stripped = title.strip()
    artist_stripped = artist.strip()
    if not title_stripped or not artist_stripped:
        return None
    if title_stripped == _DASH or artist_stripped == _DASH:
        return None
    return (_normalize_artist_for_grouping(artist), _normalize_title_for_grouping(title))


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
        return (
            0 if row.status == "complete" else 1,
            row.missing_field_count,
            len(row.title),
            row.path,
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
