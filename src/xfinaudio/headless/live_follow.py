"""Suggest what to play next from the whole library while Serato plays (S3).

The Live screen needs no generated list: it asks this method what Serato has loaded
and gets, for the newest open track that is in the library, the whole library ranked
as a continuation of it. The whole ranking reuses the engine's own rules instead of
restating them:

* ``_closest_in_bpm`` bounds the shortlist to the tracks nearest in tempo to the
  current one, then every shortlisted track is scored with ``score_transition`` from
  the current track, best first.
* The exclusion is the same one the list extension applies: no track of the current
  Serato session (open or already played), and no other version of a song of that
  session (``_is_same_song``, the same-song rule ``review.extend`` uses).
* Among the suggestions themselves two versions of one song never both appear: the
  better scored one stays and the next candidates fill the list up to
  ``MAX_SUGGESTIONS``.

The Live screen asks again every few seconds, so an answer is kept in memory together
with what it was computed from: the Serato database, the session id, the open entries,
the number of ended entries and the library revision the backend tracks. Serato's two
tables are read on every call, and a call that reads the same values returns the kept
answer without loading or scoring a single library track.

The method is read-only and answers while another job runs: it reads one snapshot of
Serato's history, the library records, and nothing else. It never creates, changes or
discards a list in progress, and no part of its answer carries a file path.

``reason`` names the only situations in which the answer has no suggestions, and is
``null`` otherwise: Serato cannot be read (``serato_not_found``, ``serato_busy``,
``serato_unreadable``), its history has no session (``no_session``), no track is
loaded on a deck or nothing is left to suggest after the current track (``nothing_playing``),
or what plays is not in the library (``not_in_library``).
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

from xfinaudio.headless.common import BackendError, _public_track
from xfinaudio.headless.serato_live import (
    SeratoEntry,
    SeratoSnapshot,
    match_library_path,
    read_serato_snapshot,
)
from xfinaudio.recommendation.playlist_service import _closest_in_bpm, _is_same_song, _same_song_key
from xfinaudio.recommendation.scoring import score_transition

if TYPE_CHECKING:
    from xfinaudio.headless.backend import HeadlessBackend
    from xfinaudio.library.models import TrackRecord

LIVE_FOLLOW_FIELDS = {"live.follow": set()}

#: The two reasons of this method; the others belong to reading Serato (S1).
NOTHING_PLAYING = "nothing_playing"
NOT_IN_LIBRARY = "not_in_library"

#: The most suggestions one answer carries.
MAX_SUGGESTIONS = 10

#: How many near-tempo tracks are scored in full before the best ten are taken.
BPM_NEIGHBOURHOOD = 200


def build_follow(records: list[TrackRecord], snapshot: SeratoSnapshot) -> dict[str, Any]:
    """The answer of ``live.follow``: what Serato plays and what to play after it."""
    library_paths = [record.path for record in records]
    by_path = {record.path: record for record in records}
    playing_pairs = [(entry, _record_for(entry, by_path, library_paths)) for entry in snapshot.playing]
    session = [record for _, record in playing_pairs if record is not None]
    session.extend(
        record for record in (_record_for(entry, by_path, library_paths) for entry in snapshot.played) if record
    )
    # ``playing`` is already newest start first, so the first match is the newest loaded
    # track the library knows: the one suggestions continue from.
    current = next((record for _, record in playing_pairs if record is not None), None)
    suggestions = [] if current is None else _suggestions(records, current, session)
    return {
        "available": snapshot.available,
        "reason": _reason(snapshot, current, suggestions),
        "sessionStartedAt": snapshot.session_started_at,
        "playing": [_playing(entry, record) for entry, record in playing_pairs],
        "current": None if current is None else _public_track(current),
        "suggestions": suggestions,
        "playedCount": len(snapshot.played),
    }


def _record_for(entry: SeratoEntry, by_path: dict[str, TrackRecord], library_paths: list[str]) -> TrackRecord | None:
    path = match_library_path(entry, library_paths)
    return None if path is None else by_path.get(path)


def _playing(entry: SeratoEntry, record: TrackRecord | None) -> dict[str, Any]:
    """One loaded deck: the library's own fields when matched, Serato's when it is not."""
    if record is not None:
        return {"deck": entry.deck, "startedAt": entry.start_time, "inLibrary": True, **_public_track(record)}
    return {
        "deck": entry.deck,
        "startedAt": entry.start_time,
        "inLibrary": False,
        "title": entry.title,
        "artist": entry.artist,
        "bpm": entry.bpm,
        "key": entry.key,
    }


def _reason(snapshot: SeratoSnapshot, current: TrackRecord | None, suggestions: list[dict[str, Any]]) -> str | None:
    """Why the answer carries no suggestions; ``None`` as soon as it carries one."""
    if not snapshot.available:
        return snapshot.reason
    if suggestions:
        return None
    if not snapshot.playing:
        return NOTHING_PLAYING
    if current is None:
        return NOT_IN_LIBRARY
    # In the library, but the rest of it offers nothing to follow it with.
    return NOTHING_PLAYING


def _suggestions(
    records: list[TrackRecord],
    current: TrackRecord,
    session: list[TrackRecord],
) -> list[dict[str, Any]]:
    """At most ``MAX_SUGGESTIONS`` library tracks to play after *current*, best first."""
    session_paths = {record.path for record in session}
    same_song_keys = [key for key in map(_same_song_key, session) if key is not None]
    candidates = [
        record
        for record in records
        if record.metadata_status == "complete"
        and record.path not in session_paths
        and not _is_same_song(record, same_song_keys)
    ]
    scored = [
        (_score_transition(current, record), record)
        for record in _closest_in_bpm(candidates, [current], BPM_NEIGHBOURHOOD)
    ]
    # The path only breaks ties, so the order is stable for a given library.
    scored.sort(key=lambda scored_track: (-scored_track[0], scored_track[1].path))
    # One version of a song per answer: the best scored one it reaches first stays and
    # its later versions are skipped, so the list still fills up to MAX_SUGGESTIONS.
    suggestions: list[dict[str, Any]] = []
    kept: list[tuple[str, str]] = []
    for score, record in scored:
        if _is_same_song(record, kept):
            continue
        suggestions.append({**_public_track(record), "score": score})
        key = _same_song_key(record)
        if key is not None:
            kept.append(key)
        if len(suggestions) == MAX_SUGGESTIONS:
            break
    return suggestions


def _score_transition(current: TrackRecord, candidate: TrackRecord) -> float:
    """The engine's own transition score from *current* to *candidate*, inside 0..1."""
    total = score_transition(current, candidate).total_score
    return min(1.0, max(0.0, total))


class LiveFollow:
    """Answer the Live screen from Serato and the library, without touching either."""

    def __init__(self, backend: HeadlessBackend) -> None:
        self.backend = backend
        # The last answer and what it was computed from; lost with this process.
        self._kept: tuple[tuple[Any, ...], dict[str, Any]] | None = None

    def execute(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method not in LIVE_FOLLOW_FIELDS:
            raise BackendError("unknown_method", "Unknown command")
        if params:
            raise BackendError("invalid_params", "Unexpected command parameters")
        snapshot = read_serato_snapshot(self.backend.serato_database_path)
        key = self._key(snapshot)
        if self._kept is not None and self._kept[0] == key:
            return copy.deepcopy(self._kept[1])
        answer = build_follow(self.backend._records(), snapshot)
        self._kept = (key, copy.deepcopy(answer))
        return answer

    def _key(self, snapshot: SeratoSnapshot) -> tuple[Any, ...]:
        """Everything the answer was computed from, cheap to compare on every poll."""
        return (
            str(self.backend.serato_database_path),
            snapshot.session_id,
            snapshot.reason,
            tuple((entry.deck, entry.start_time) for entry in snapshot.playing),
            len(snapshot.played),
            self.backend.library_revision(),
        )
