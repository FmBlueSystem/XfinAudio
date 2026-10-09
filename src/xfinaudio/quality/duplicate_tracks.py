"""Deterministic repeated-track detection for generated playlists.

Layer-neutral and read-only: groups `TrackRecord` values that are likely the
same song or the same recording, so the DJ readiness report can flag repeats
advisory-style (`needs_review`, never `blocked`). Two rules:

- **Rule A — same song:** two tracks share the strict candidate-pool grouping
  key (`playlist_duplicate_group_key`), the battle-tested normalizer that
  strips `[DJ Edit]`, `(Single Version)`, `Mix by ...`, `feat.` credits, etc.
- **Rule B — same recording with damaged title metadata:** the real-world case
  where one library copy lost part of its title (e.g. `9 To 5 [DJ Edit]` vs
  `To 5 (DJ Edit)`, both Dolly Parton, 2:33, 105.02 BPM). Equal normalized
  artist, duration within `DURATION_TOLERANCE_SECONDS` and BPM within
  `BPM_TOLERANCE_PERCENT` (half-time notation folds, so 52.51 ≈ 105.02) are
  treated as the same recording when one normalized title contains the other
  (`_MIN_DAMAGED_TITLE_CHARS` minimum): a damaged copy keeps the rest of the
  title, while genuinely different songs of the same tempo do not overlap.

Rule B never fires on equal normalized titles (that is rule A's job) and never
fires without both a duration and a BPM, keeping false positives rare and every
group explainable to the DJ.
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from xfinaudio.library.duplicate_grouping import (
    normalize_artist_for_playlist_grouping,
    normalize_title_for_playlist_grouping,
    playlist_duplicate_group_key,
)
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.scoring import bpm_difference_percent

SAME_SONG = "misma-canción"
SAME_RECORDING = "grabación-duplicada"

DURATION_TOLERANCE_SECONDS = 2.0
BPM_TOLERANCE_PERCENT = 0.5
_MIN_DAMAGED_TITLE_CHARS = 3

_MAX_DETAIL_GROUPS = 3


class DuplicateTrackGroup(BaseModel):
    """One group of likely-repeated tracks, positions are 1-based playlist order."""

    model_config = ConfigDict(frozen=True)

    positions: tuple[int, ...]
    paths: tuple[str, ...]
    titles: tuple[str, ...]
    artists: tuple[str, ...]
    reason: str


def find_duplicate_groups(tracks: Sequence[TrackRecord]) -> list[DuplicateTrackGroup]:
    """Return deterministic groups of likely-repeated tracks in playlist order."""
    parent = list(range(len(tracks)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for left in range(len(tracks)):
        for right in range(left + 1, len(tracks)):
            if _are_duplicates(tracks[left], tracks[right]):
                parent[find(right)] = find(left)

    groups: list[DuplicateTrackGroup] = []
    by_root: dict[int, list[int]] = {}
    for index in range(len(tracks)):
        by_root.setdefault(find(index), []).append(index)
    for members in by_root.values():
        if len(members) < 2:
            continue
        members.sort()
        groups.append(
            DuplicateTrackGroup(
                positions=tuple(index + 1 for index in members),
                paths=tuple(tracks[index].path for index in members),
                titles=tuple(tracks[index].title or "" for index in members),
                artists=tuple(tracks[index].artist or "" for index in members),
                reason=_group_reason(tracks, members),
            )
        )
    groups.sort(key=lambda group: group.positions[0])
    return groups


def format_duplicate_detail(groups: Sequence[DuplicateTrackGroup]) -> str:
    """Render the human-readable detail line used by the readiness check."""
    parts = [
        " ≈ ".join(f"'{title}'" for title in group.titles)
        + f" (posiciones {' y '.join(_position_words(group.positions))})"
        for group in groups[:_MAX_DETAIL_GROUPS]
    ]
    detail = f"{len(groups)} grupo(s) de posibles pistas repetidas: " + "; ".join(parts)
    hidden = len(groups) - _MAX_DETAIL_GROUPS
    if hidden > 0:
        detail += f"; y {hidden} grupo(s) más"
    return detail


def _position_words(positions: tuple[int, ...]) -> list[str]:
    """Render 1-based positions so two tracks read "1 y 2", three read "1, 2 y 3"."""
    if len(positions) <= 2:
        return [str(position) for position in positions]
    return [", ".join(str(position) for position in positions[:-1]), str(positions[-1])]


def _group_reason(tracks: Sequence[TrackRecord], members: list[int]) -> str:
    for index, left in enumerate(members):
        left_key = _same_song_key(tracks[left])
        if left_key is None:
            continue
        for right in members[index + 1 :]:
            if left_key == _same_song_key(tracks[right]):
                return SAME_SONG
    return SAME_RECORDING


def _are_duplicates(left: TrackRecord, right: TrackRecord) -> bool:
    left_key = _same_song_key(left)
    if left_key is not None and left_key == _same_song_key(right):
        return True
    return _suspected_same_recording(left, right)


def _same_song_key(track: TrackRecord) -> tuple[str, str] | None:
    return playlist_duplicate_group_key(track.title, track.artist)


def _suspected_same_recording(left: TrackRecord, right: TrackRecord) -> bool:
    left_artist = normalize_artist_for_playlist_grouping(left.artist or "")
    right_artist = normalize_artist_for_playlist_grouping(right.artist or "")
    if not left_artist or left_artist != right_artist:
        return False
    left_title = normalize_title_for_playlist_grouping(left.title or "")
    right_title = normalize_title_for_playlist_grouping(right.title or "")
    if not left_title or not right_title or left_title == right_title:
        return False
    shorter, longer = sorted((left_title, right_title), key=len)
    if len(shorter) < _MIN_DAMAGED_TITLE_CHARS or shorter not in longer:
        return False
    if left.duration is None or right.duration is None:
        return False
    if abs(left.duration - right.duration) > DURATION_TOLERANCE_SECONDS:
        return False
    if left.bpm is None or right.bpm is None:
        return False
    return bpm_difference_percent(left.bpm, right.bpm) <= BPM_TOLERANCE_PERCENT


__all__ = [
    "SAME_RECORDING",
    "SAME_SONG",
    "DuplicateTrackGroup",
    "find_duplicate_groups",
    "format_duplicate_detail",
]
