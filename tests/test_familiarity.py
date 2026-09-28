"""Tests for the opt-in familiarity preference signal (Plan 3 T3).

The signal is aggregated from read-only Serato play history and crate
membership. It must stay INERT unless a caller explicitly provides signals
and a nonzero weight, and it must never block a track: it only reorders.
"""

from __future__ import annotations

from datetime import UTC, datetime

from xfinaudio.exporting.serato_history import ParsedSeratoHistorySession
from xfinaudio.recommendation.familiarity import FamiliaritySignal, aggregate_familiarity


def session(path: str | None, played_at: datetime | None = None) -> ParsedSeratoHistorySession:
    return ParsedSeratoHistorySession(
        track_path=path,
        title=None,
        artist=None,
        played_at=played_at,
        unknown_fields=(),
    )


def test_aggregate_counts_multiple_sessions_of_same_path_and_keeps_latest_played_at():
    early = datetime(2026, 1, 1, tzinfo=UTC)
    late = datetime(2026, 3, 1, tzinfo=UTC)
    signals = aggregate_familiarity(
        [session("/a.mp3", early), session("/a.mp3", late), session("/a.mp3", early)],
        {},
    )
    assert signals == {"/a.mp3": FamiliaritySignal(play_count=3, last_played=late, crate_count=0)}


def test_aggregate_joins_crate_membership_with_zero_default():
    signals = aggregate_familiarity([session("/a.mp3")], {"/a.mp3": 4, "/other.mp3": 2})
    assert signals["/a.mp3"] == FamiliaritySignal(play_count=1, last_played=None, crate_count=4)


def test_aggregate_empty_inputs_yield_empty_mapping():
    assert aggregate_familiarity([], {}) == {}


def test_aggregate_skips_sessions_without_track_path():
    signals = aggregate_familiarity([session(None), session("/a.mp3")], {})
    assert set(signals) == {"/a.mp3"}


def test_aggregate_does_not_emit_signals_for_crate_only_paths():
    # The aggregation is an inner join on session-derived paths: a track that
    # appears in crates but was never played has no play-history signal yet.
    # Crate-only membership is deliberately not emitted (documented decision).
    assert aggregate_familiarity([], {"/a.mp3": 3}) == {}
