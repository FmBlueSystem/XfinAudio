"""Read-only library health analyzer.

Scores the metadata quality of a scanned library and surfaces the mixing-relevant issues a DJ can
fix: missing key/BPM/energy, suspicious (half-/double-time) BPM, and inconsistent genre spelling.
It never mutates audio, the library database, or any Serato file — it only reads ``TrackRecord``.

Scope note: file-level duplicate detection is deliberately NOT here. The OS and dedicated tools
(checksum-based dedupers, DJ software) already do that far better; XfinAudio is decision-support
for building sets, not a file manager. This analyzer only covers metadata the OS cannot judge and
that directly affects playlist quality.
"""

from __future__ import annotations

import re
from collections import defaultdict

from pydantic import BaseModel, ConfigDict

from xfinaudio.genre.effective_genre import effective_genre
from xfinaudio.library.models import TrackRecord

# A track BPM below/above this DJ-sane range is almost always a half-/double-time detection error.
_MIN_SANE_BPM = 60.0
_MAX_SANE_BPM = 200.0

_GENRE_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


class LibraryHealthReport(BaseModel):
    """Aggregated metadata-quality snapshot for a scanned library."""

    model_config = ConfigDict(frozen=True)

    total: int
    complete: int
    missing_key: int
    missing_bpm: int
    missing_energy: int
    suspicious_bpm: int
    genre_variant_groups: int
    health_score: float


def _normalize_genre(genre: str) -> str:
    return _GENRE_NORMALIZE_RE.sub("", genre.casefold())


def _is_suspicious_bpm(bpm: float | None) -> bool:
    return bpm is not None and (bpm < _MIN_SANE_BPM or bpm > _MAX_SANE_BPM)


def _is_clean(track: TrackRecord) -> bool:
    """A track is clean when it has all required fields and no suspicious BPM."""
    return (
        track.camelot_key is not None
        and track.bpm is not None
        and track.energy_level is not None
        and not _is_suspicious_bpm(track.bpm)
    )


def analyze_library_health(tracks: list[TrackRecord]) -> LibraryHealthReport:
    """Return a deterministic health report for the given tracks."""
    total = len(tracks)
    if total == 0:
        return LibraryHealthReport(
            total=0,
            complete=0,
            missing_key=0,
            missing_bpm=0,
            missing_energy=0,
            suspicious_bpm=0,
            genre_variant_groups=0,
            health_score=1.0,
        )

    missing_key = sum(1 for t in tracks if t.camelot_key is None)
    missing_bpm = sum(1 for t in tracks if t.bpm is None)
    missing_energy = sum(1 for t in tracks if t.energy_level is None)
    suspicious_bpm = sum(1 for t in tracks if _is_suspicious_bpm(t.bpm))
    complete = sum(1 for t in tracks if t.metadata_status == "complete")
    clean = sum(1 for t in tracks if _is_clean(t))

    # Genre spelling variants: one normalized genre with more than one raw spelling.
    # Operates on the effective (canonical when available, else raw) genre so
    # enriched libraries collapse onto the canonical taxonomy.
    raw_by_normalized: dict[str, set[str]] = defaultdict(set)
    for track in tracks:
        genre = effective_genre(track)
        if genre and genre.strip():
            raw_by_normalized[_normalize_genre(genre)].add(genre.strip())
    genre_variant_groups = sum(1 for spellings in raw_by_normalized.values() if len(spellings) > 1)

    return LibraryHealthReport(
        total=total,
        complete=complete,
        missing_key=missing_key,
        missing_bpm=missing_bpm,
        missing_energy=missing_energy,
        suspicious_bpm=suspicious_bpm,
        genre_variant_groups=genre_variant_groups,
        health_score=round(clean / total, 4),
    )


__all__ = ["LibraryHealthReport", "analyze_library_health"]
