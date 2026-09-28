"""Opt-in familiarity preference signal aggregated from read-only Serato data.

Pure domain module: no Qt/desktop imports. The signal is INERT BY DEFAULT —
it only affects recommendations when a caller explicitly provides aggregated
signals and a nonzero weight (production wiring: only when
``SeratoIntegrationSettings.enabled`` and the user's Serato directory yields
data).

Familiarity NEVER blocks a track: it only informs scoring/ordering at the
candidate-pool seam (`xfinaudio.recommendation.candidate_pool`); an
unfamiliar track is never dropped, filtered, or gated because of it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from xfinaudio.exporting.serato_history import ParsedSeratoHistorySession


@dataclass(frozen=True)
class FamiliaritySignal:
    """Per-track familiarity evidence from Serato history and crates.

    ``play_count`` counts how many history sessions mention the track;
    ``last_played`` is the latest session timestamp (``None`` when no session
    carried one); ``crate_count`` is the number of crates containing the
    track (``0`` default).
    """

    play_count: int
    last_played: datetime | None
    crate_count: int


def aggregate_familiarity(
    sessions: Sequence[ParsedSeratoHistorySession],
    membership: Mapping[str, int],
) -> dict[str, FamiliaritySignal]:
    """Aggregate Serato history sessions and crate membership per track path.

    Sessions are grouped by ``track_path`` (play count plus the latest
    ``played_at``); crate counts join onto those paths, defaulting to ``0``.
    Sessions without a ``track_path`` are skipped (nothing to key on). The
    join is an inner join on session-derived paths: a track that appears in
    crates but was never played emits no signal (crate membership alone is
    not yet treated as familiarity — revisit if a future task promotes it).
    Empty inputs aggregate to an empty mapping.
    """
    play_counts: dict[str, int] = {}
    last_played: dict[str, datetime] = {}
    for session in sessions:
        path = session.track_path
        if path is None:
            continue
        play_counts[path] = play_counts.get(path, 0) + 1
        if session.played_at is not None:
            existing = last_played.get(path)
            if existing is None or session.played_at > existing:
                last_played[path] = session.played_at
    return {
        path: FamiliaritySignal(
            play_count=play_counts[path],
            last_played=last_played.get(path),
            crate_count=membership.get(path, 0),
        )
        for path in play_counts
    }
