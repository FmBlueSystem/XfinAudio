"""Search the local library for the list assistant, exposing only public fields.

One turn may ask for up to two searches. They run here, locally, over the records the
core already stores: a track is offered only when its metadata is complete, it is not
in the list and the plan does not exclude it. The text matches the same way the
Library's own text filter does (title, artist and genre), and the closest BPM to the
list comes first, because that is the track the engine could actually swap in.

What leaves this module for the provider is a short conversation-scoped reference
(``L1``, ``L2``...) plus title, artist, genre, BPM, key, energy, duration and release
year. A file path and a public track identity never leave it.
"""

from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from xfinaudio.library.models import TrackRecord
from xfinaudio.metadata.tempo import is_valid_bpm
from xfinaudio.recommendation.playlist_service import in_plan_period

if TYPE_CHECKING:
    from collections.abc import Sequence

    from xfinaudio.ai.list_chat import SearchQuery
    from xfinaudio.headless.backend import HeadlessBackend

#: The most results one search returns, so one extra request still fits the UI.
MAX_SEARCH_RESULTS = 20


@dataclass(frozen=True)
class LibraryMatch:
    """One executed search and the eligible tracks it found, closest in BPM first."""

    query: SearchQuery
    records: tuple[TrackRecord, ...]

    def public(self) -> dict[str, Any]:
        """The search exactly as the opt-in chat log records it: never a title or a path."""
        return {**self.query.public(), "resultCount": len(self.records)}


def search_library(backend: HeadlessBackend, queries: Sequence[SearchQuery]) -> tuple[LibraryMatch, ...]:
    """Run each search over the library, in the order the assistant asked for them."""
    review, plan = backend.review, backend.plan
    if review is None or plan is None:
        return tuple(LibraryMatch(query, ()) for query in queries)
    listed = {track.path for track in review.recommendation.ordered_tracks}
    excluded = set(plan.intent.excluded_paths)
    listed_bpms = [track.bpm for track in review.recommendation.ordered_tracks]
    anchors = [bpm for bpm in listed_bpms if bpm is not None and is_valid_bpm(bpm)]
    # The command's own snapshot already holds every record, so this reads no file.
    # S17: a list the DJ generated with a release period only searches inside it, so a
    # search can never offer a track the period rules out.
    eligible = [
        record
        for record in backend._records(checked=frozenset())
        if record.path not in listed
        and record.path not in excluded
        and record.metadata_status == "complete"
        and in_plan_period(record, plan.intent.year_min, plan.intent.year_max)
    ]
    return tuple(LibraryMatch(query, _execute(query, eligible, anchors)) for query in queries)


def public_result(reference: str, record: TrackRecord) -> dict[str, Any]:
    """One result as the provider reads it: its reference and the DJ-visible fields only."""
    return {
        "reference": reference,
        "title": record.title or Path(record.path).stem,
        "artist": record.artist or "",
        "genre": record.genre or "",
        "bpm": record.bpm if is_valid_bpm(record.bpm) else None,
        "key": record.camelot_key,
        "energy": record.energy_level,
        "duration": record.duration,
        "year": record.release_year,
    }


def _execute(query: SearchQuery, records: list[TrackRecord], anchors: Sequence[float]) -> tuple[TrackRecord, ...]:
    """The eligible tracks this search matches, closest in BPM to the list first."""
    matched = [record for record in records if _matches(query, record)]
    matched.sort(key=lambda record: _rank(record, anchors))
    return tuple(matched[:MAX_SEARCH_RESULTS])


def _matches(query: SearchQuery, record: TrackRecord) -> bool:
    """Whether one record satisfies every field of the search, exactly as the Library does."""
    if query.query and not any(
        _plain(query.query) in _plain(value or "") for value in (record.title, record.artist, record.genre)
    ):
        return False
    if query.genre and query.genre.casefold() != (record.genre or "").casefold():
        return False
    if query.key and query.key != (record.camelot_key or "").upper():
        return False
    if not _in_years(query.year_min, query.year_max, record.release_year):
        return False
    return _within(query.bpm_min, query.bpm_max, record.bpm)


def _in_years(low: int | None, high: int | None, value: int | None) -> bool:
    """Whether one release year satisfies a search range; an unknown year never does."""
    if low is None and high is None:
        return True
    if value is None or value <= 0:
        return False
    return (low is None or value >= low) and (high is None or value <= high)


def _within(low: float | None, high: float | None, value: float | None) -> bool:
    """Whether one BPM value satisfies a search range; a missing value never does."""
    if low is None and high is None:
        return True
    if value is None or not math.isfinite(value) or value <= 0:
        return False
    return (low is None or value >= low) and (high is None or value <= high)


def _rank(record: TrackRecord, anchors: Sequence[float]) -> tuple[bool, float, str, str]:
    """Order by BPM closeness to the list, then deterministically; a missing BPM goes last."""
    title = (record.title or "").casefold()
    bpm = record.bpm
    if bpm is None or not is_valid_bpm(bpm):
        return (True, math.inf, title, record.path)
    closest = min((abs(bpm - anchor) for anchor in anchors), default=math.inf)
    return (False, closest, title, record.path)


def _plain(text: str) -> str:
    """Casefolded text without accents, so a search matches the Library's own text filter."""
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c))


__all__ = ["MAX_SEARCH_RESULTS", "LibraryMatch", "public_result", "search_library"]
