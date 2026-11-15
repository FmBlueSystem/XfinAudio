"""Read-only genre catalog for the Prep genre picker, ordered compatible-first.

The picker never invents an ordering: the library's genres, their track counts
and the compatible-first ranking are all computed here, from the same scoring
rules the engine already uses. Genres are grouped by the engine's own
casefolded whole-string match (``_normalized_genre`` in ``playlist_service``),
so "Deep House" and "deep house" are one genre, counted once and displayed with
the spelling stored on the track whose path sorts first.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from xfinaudio.headless.common import BackendError, _public_track
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.candidate_pool import _track_similarity_key, _track_vibe_terms
from xfinaudio.recommendation.playlist_service import _normalized_genre

if TYPE_CHECKING:
    from xfinaudio.headless.backend import HeadlessBackend

GENRE_FIELDS = {"prep.genres": {"startTrackId", "genre"}}
_TRACK_ID = re.compile(r"[0-9a-f]{64}")
_MAX_REQUESTED_GENRE = 100

# The candidate pool's similarity key already buckets exactly the three rules the
# picker needs: BPM (0 = within 3 BPM, 1 = within 6, after half/double-time
# normalization), Camelot key (0 = identical, 1 = 0.90, 2 = 0.85) and raw energy
# distance. Reading those buckets keeps this ranking identical to the engine's
# instead of duplicating the thresholds here; anything past them -- including
# missing metadata, which the pool ranks last -- is not a compatible genre.
_COMPATIBLE_BPM_BUCKETS = 1
_COMPATIBLE_KEY_BUCKETS = 2
_COMPATIBLE_ENERGY_DISTANCE = 1


@dataclass(frozen=True)
class _Genre:
    key: str
    name: str
    count: int
    tracks: tuple[TrackRecord, ...]


def _index(records: list[TrackRecord]) -> list[_Genre]:
    """Group the library's genres case-insensitively, keeping one stored spelling each."""
    grouped: dict[str, list[TrackRecord]] = {}
    names: dict[str, str] = {}
    for record in sorted(records, key=lambda item: item.path):
        key = _normalized_genre(record)
        if key is None:
            continue
        grouped.setdefault(key, []).append(record)
        names.setdefault(key, (record.genre or "").strip())
    return [
        _Genre(key=key, name=names[key], count=len(tracks), tracks=tuple(tracks)) for key, tracks in grouped.items()
    ]


def _mixes_with(seed: TrackRecord, genre: _Genre, seed_terms: set[str]) -> bool:
    """Whether any of the genre's tracks is one the engine would rank next to the seed."""
    if seed.metadata_status != "complete":
        return False
    for track in genre.tracks:
        if track.path == seed.path or track.metadata_status != "complete":
            continue
        bpm_bucket, key_bucket, _overlap, energy_distance, _bpm, _path = _track_similarity_key(
            seed_terms, [seed], track
        )
        if (
            bpm_bucket <= _COMPATIBLE_BPM_BUCKETS
            and key_bucket <= _COMPATIBLE_KEY_BUCKETS
            and energy_distance <= _COMPATIBLE_ENERGY_DISTANCE
        ):
            return True
    return False


def _option(genre: _Genre) -> dict[str, Any]:
    return {"name": genre.name, "count": genre.count}


def _available(genres: list[_Genre], requested: Any) -> bool:
    wanted = (requested or "").strip().casefold() if isinstance(requested, str) else ""
    if not wanted:
        return True
    return any(genre.key == wanted for genre in genres)


def build_catalog(records: list[TrackRecord], *, seed: TrackRecord | None, requested: Any) -> dict[str, Any]:
    """Serialize the genre groups: compatible-first with a seed, most-used first without one."""
    genres = _index(records)
    by_count = sorted(genres, key=lambda genre: (-genre.count, genre.key))
    groups: list[dict[str, Any]] = []
    if seed is None:
        if by_count:
            groups.append({"kind": "library", "genres": [_option(genre) for genre in by_count]})
    else:
        seed_key = _normalized_genre(seed)
        seed_terms = _track_vibe_terms(seed)
        own = next((genre for genre in genres if genre.key == seed_key), None)
        compatible = [genre for genre in by_count if own is None or genre.key != own.key]
        compatible = [genre for genre in compatible if _mixes_with(seed, genre, seed_terms)]
        compatible.sort(key=lambda genre: (-genre.count, genre.key))
        first = [_option(own)] if own is not None else []
        if first or compatible:
            groups.append({"kind": "compatible", "genres": [*first, *[_option(genre) for genre in compatible]]})
        matched = {genre.key for genre in compatible}
        if own is not None:
            matched.add(own.key)
        rest = [genre for genre in sorted(genres, key=lambda genre: genre.key) if genre.key not in matched]
        if rest:
            groups.append({"kind": "library", "genres": [_option(genre) for genre in rest]})
    return {
        "groups": groups,
        "totalGenres": len(genres),
        "seedTitle": None if seed is None else _public_track(seed)["title"],
        "genreAvailable": _available(genres, requested),
    }


class GenreCatalog:
    """Serve the library's genres with the same read-only, fail-closed posture as library.list."""

    def __init__(self, backend: HeadlessBackend) -> None:
        self.backend = backend

    def execute(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method not in GENRE_FIELDS:
            raise BackendError("unknown_method", "Unknown command")
        records = self.backend._records()
        seed: TrackRecord | None = None
        if "startTrackId" in params:
            track_id = params["startTrackId"]
            if not isinstance(track_id, str) or _TRACK_ID.fullmatch(track_id) is None:
                raise BackendError("invalid_params", "Invalid opening track identity")
            path = self.backend._track_paths.get(track_id)
            seed = next((record for record in records if record.path == path), None) if path is not None else None
            if seed is None:
                raise BackendError("not_found", "The opening track is not in an authorized library")
        requested = params.get("genre")
        if requested is not None and (
            not isinstance(requested, str) or len(requested) > _MAX_REQUESTED_GENRE or "\x00" in requested
        ):
            raise BackendError("invalid_params", "Invalid genre")
        return build_catalog(records, seed=seed, requested=requested)
