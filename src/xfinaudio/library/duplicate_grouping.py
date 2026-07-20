"""Layer-neutral duplicate-version grouping core — no Qt, no desktop imports.

Relocated from `desktop/library_filter.py` (design.md Decision 3a) so that
both the Library-screen display filter and the recommendation candidate pool
share the exact same grouping semantics without `recommendation/` importing
`desktop/`. The `_DASH` placeholder check becomes the `placeholder` parameter:
`desktop/library_filter.py` passes the display-dash literal, the
recommendation pool passes `None` (no placeholder special-case, only
blank/None values force a singleton).
"""

from __future__ import annotations

import re

# Trailing " - <CamelotKey> - Energy <N>" suffix, e.g. " - 12A - Energy 7".
# Camelot key anchored to the real shape: 1-12 followed by A or B (real-case text).
_CAMELOT_ENERGY_SUFFIX = re.compile(r"\s*-\s*(?:[1-9]|1[0-2])[AB]\s*-\s*Energy\s+\d+\s*$")

# Trailing "(vN)" version marker, e.g. "(v2)".
_VERSION_SUFFIX = re.compile(r"\s*\(v\d+\)\s*$")

# Any parenthetical group and its content, e.g. "(Clean)", "(Single Version)".
_PARENTHETICAL_CONTENT = re.compile(r"\([^)]*\)")


def _strip_generated_suffixes(text: str) -> str:
    """Repeatedly strip trailing app-generated technical suffixes.

    Shared by both the conservative (library display) and the stricter
    (playlist pool) title normalizers — suffix stripping happens against the
    original-case text (the regex is written for real-case text like
    "Energy"/"A"/"B"); casefolding is the caller's responsibility, done last.
    """
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
    return text


def normalize_title_for_grouping(title: str) -> str:
    """Strip app-generated technical suffixes, repeatedly, then casefold.

    Suffix stripping happens against the original-case text first (the regex is
    written for real-case text like "Energy"/"A"/"B") — casefolding happens last.
    Remix/edit/mix descriptor *content* is never touched, but the parentheses
    around it are stripped as punctuation: real-world exports are inconsistent
    about wrapping a descriptor in parens (e.g. "Song (Remix)" vs "Song Remix"
    for the exact same file), so treating "(" / ")" as opaque would fail to
    group those two forms of the same descriptor together — which defeats the
    whole point of this feature for exactly that case.

    This is the conservative key used by the Library screen's display-only
    duplicate filter. `normalize_title_for_playlist_grouping` is the stricter,
    playlist-pool-only variant (maintainer decision 2026-07-20).
    """
    text = _strip_generated_suffixes(title.strip())
    text = text.replace("(", " ").replace(")", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text.casefold()


def normalize_title_for_playlist_grouping(title: str) -> str:
    """Strip app-generated suffixes AND parenthetical descriptor content entirely.

    Stricter than `normalize_title_for_grouping`: maintainer decision
    2026-07-20 established that, for recommendation candidate-pool purposes,
    "Too Hot (Clean)" and "Too Hot (Single Version)" are the same song —
    unlike the Library screen's display filter, which intentionally keeps
    distinct parenthetical descriptors visible as separate versions. This
    function is used ONLY by `playlist_duplicate_group_key`
    (`recommendation/candidate_pool.py`'s dedupe step); the Library display
    filter continues to use `normalize_title_for_grouping` unchanged.
    """
    text = _strip_generated_suffixes(title.strip())
    text = _PARENTHETICAL_CONTENT.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.casefold()


def normalize_artist_for_grouping(artist: str) -> str:
    """Strip whitespace and casefold — no suffix stripping for artist names."""
    return artist.strip().casefold()


def duplicate_group_key(
    title: str | None, artist: str | None, *, placeholder: str | None = None
) -> tuple[str, str] | None:
    """Return the grouping key for *title*/*artist*, or None to force a singleton.

    None/blank title or artist is never grouped, since blank metadata tracks
    must never collapse into a fake "duplicate" group. When *placeholder* is
    given, a title or artist exactly equal to it (e.g. the display-layer's
    dash placeholder for missing metadata) is treated the same as blank.
    """
    if title is None or artist is None:
        return None
    title_stripped = title.strip()
    artist_stripped = artist.strip()
    if not title_stripped or not artist_stripped:
        return None
    if placeholder is not None and (title_stripped == placeholder or artist_stripped == placeholder):
        return None
    return (normalize_artist_for_grouping(artist), normalize_title_for_grouping(title))


def playlist_duplicate_group_key(title: str | None, artist: str | None) -> tuple[str, str] | None:
    """Return the recommendation candidate-pool grouping key.

    Stricter than `duplicate_group_key`: uses
    `normalize_title_for_playlist_grouping` (parenthetical descriptor content
    removed entirely) rather than the conservative
    `normalize_title_for_grouping`. None/blank title or artist is never
    grouped. No placeholder special-case — the recommendation pool has no
    display-layer dash-placeholder concept.
    """
    if title is None or artist is None:
        return None
    title_stripped = title.strip()
    artist_stripped = artist.strip()
    if not title_stripped or not artist_stripped:
        return None
    normalized_title = normalize_title_for_playlist_grouping(title)
    if not normalized_title:
        # Fully-parenthetical titles (e.g. "(Intro)", "(Outro)") normalize to
        # an empty string once descriptor content is stripped — never collapse
        # distinct titles onto a shared "(artist, '')" key.
        return None
    return (normalize_artist_for_grouping(artist), normalized_title)


def duplicate_representative_sort_key(
    *, is_complete: bool, missing_field_count: int, title: str, path: str
) -> tuple[int, int, int, str]:
    """Return the ordering key used to pick the representative of a duplicate group.

    Order: (1) complete status first, (2) lower missing-field count,
    (3) shortest original title, (4) alphabetical path as final tiebreak.
    """
    return (
        0 if is_complete else 1,
        missing_field_count,
        len(title),
        path,
    )


__all__ = [
    "duplicate_group_key",
    "duplicate_representative_sort_key",
    "normalize_artist_for_grouping",
    "normalize_title_for_grouping",
    "normalize_title_for_playlist_grouping",
    "playlist_duplicate_group_key",
]
