"""Tests for ReviewViewModel — readiness semaphore as primary output."""

from __future__ import annotations

import pytest

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.review_view_model import (
    ReadinessCheckRow,
    ReadinessStatus,
    RecommendationRow,
    ReviewViewModel,
    TransitionRow,
)
from xfinaudio.exporting.explainability import PlaylistExplanation, TrackExplanation, TransitionExplanation
from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.dj_readiness import DjReadinessCheck, DjReadinessReport
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.scoring import ScoringWeights
from xfinaudio.recommendation.strategies import PlaylistStrategy

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_track(path: str = "track.mp3", title: str = "Test Track", artist: str = "DJ Test") -> TrackRecord:
    return TrackRecord(
        path=path,
        title=title,
        artist=artist,
        bpm=128.0,
        camelot_key="8A",
        energy_level=7,
        metadata_status="complete",
    )


def _make_strategy() -> PlaylistStrategy:
    return PlaylistStrategy(
        name="harmonic_journey",
        display_name="Harmonic Flow",
        description="",
        weights=ScoringWeights(),
    )


def _make_recommendation(tracks: list[TrackRecord] | None = None) -> PlaylistRecommendation:
    if tracks is None:
        tracks = [_make_track("a.mp3", "Track A", "Artist A")]
    return PlaylistRecommendation(
        ordered_tracks=tracks,
        transition_scores=[],
        strategy=_make_strategy(),
        warnings=[],
        applied_controls={},
        optimizer="test",
        total_score=0.0,
    )


def _make_readiness(status: str, checks: list[DjReadinessCheck] | None = None) -> DjReadinessReport:
    if checks is None:
        checks = [
            DjReadinessCheck(label="Playlist size", status="ready", detail="2 tracks available"),
        ]
    blocker_count = sum(1 for c in checks if c.status == "blocked")
    review_count = sum(1 for c in checks if c.status == "needs_review")
    return DjReadinessReport(
        status=status,
        summary=f"Status: {status}",
        checks=checks,
        blocker_count=blocker_count,
        review_count=review_count,
    )


def _make_quality_report() -> RecommendationQualityReport:
    return RecommendationQualityReport(
        track_count=1,
        transition_count=1,
        average_transition_score=0.85,
        bpm_jumps=[2.0],
        energy_jumps=[1],
        warning_count=0,
    )


def _make_track_explanation(title: str = "Track", artist: str = "Artist") -> TrackExplanation:
    return TrackExplanation(
        path=f"{title}.mp3",
        title=title,
        artist=artist,
        bpm=128.0,
        camelot_key="8A",
        energy_level=7,
        metadata_status="complete",
    )


def _make_transition_explanation(
    from_title: str = "Track A",
    to_title: str = "Track B",
    final_score: float = 0.85,
    warnings: list[str] | None = None,
) -> TransitionExplanation:
    return TransitionExplanation(
        order=1,
        left=_make_track_explanation(from_title),
        right=_make_track_explanation(to_title),
        component_scores={"bpm": 0.9, "harmonic": 0.8},
        final_score=final_score,
        warnings=warnings or [],
        explanations=[],
    )


def _make_playlist_explanation(transitions: list[TransitionExplanation] | None = None) -> PlaylistExplanation:
    if transitions is None:
        transitions = [_make_transition_explanation()]
    return PlaylistExplanation(
        strategy="harmonic",
        optimizer="greedy",
        track_count=2,
        transition_count=len(transitions),
        total_score=sum(t.final_score for t in transitions),
        warnings=[],
        transitions=transitions,
    )


# ---------------------------------------------------------------------------
# State builders
# ---------------------------------------------------------------------------


def _state_with_recommendation_no_readiness() -> AppState:
    state = AppState()
    state.last_recommendation = _make_recommendation()
    return state


def _state_with_readiness(status: str) -> AppState:
    state = AppState()
    state.last_recommendation = _make_recommendation()
    state.last_dj_readiness_report = _make_readiness(status)
    return state


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def vm() -> ReviewViewModel:
    return ReviewViewModel()


# ---------------------------------------------------------------------------
# readiness_status
# ---------------------------------------------------------------------------


class TestReadinessStatus:
    def test_blocked_when_no_recommendation(self, vm: ReviewViewModel) -> None:
        assert vm.readiness_status(AppState()) == ReadinessStatus.BLOCKED

    def test_needs_review_when_recommendation_but_no_readiness(self, vm: ReviewViewModel) -> None:
        state = _state_with_recommendation_no_readiness()
        assert vm.readiness_status(state) == ReadinessStatus.NEEDS_REVIEW

    def test_ready_when_readiness_is_ready(self, vm: ReviewViewModel) -> None:
        state = _state_with_readiness("ready")
        assert vm.readiness_status(state) == ReadinessStatus.READY

    def test_blocked_when_readiness_is_blocked(self, vm: ReviewViewModel) -> None:
        state = _state_with_readiness("blocked")
        assert vm.readiness_status(state) == ReadinessStatus.BLOCKED

    def test_needs_review_when_readiness_is_needs_review(self, vm: ReviewViewModel) -> None:
        state = _state_with_readiness("needs_review")
        assert vm.readiness_status(state) == ReadinessStatus.NEEDS_REVIEW


# ---------------------------------------------------------------------------
# readiness_badge_text
# ---------------------------------------------------------------------------


class TestReadinessBadgeText:
    def test_no_playlist_when_no_recommendation(self, vm: ReviewViewModel) -> None:
        assert vm.readiness_badge_text(AppState()) == "No playlist generated"

    def test_blocked_text_contains_blocked(self, vm: ReviewViewModel) -> None:
        state = _state_with_readiness("blocked")
        assert "blocked" in vm.readiness_badge_text(state).lower()

    def test_ready_text_contains_ready(self, vm: ReviewViewModel) -> None:
        state = _state_with_readiness("ready")
        assert "Ready" in vm.readiness_badge_text(state)

    def test_needs_review_text_contains_review(self, vm: ReviewViewModel) -> None:
        state = _state_with_readiness("needs_review")
        assert "review" in vm.readiness_badge_text(state).lower()

    def test_ready_says_ready_to_export(self, vm: ReviewViewModel) -> None:
        state = _state_with_readiness("ready")
        assert vm.readiness_badge_text(state) == "Ready to export"

    def test_needs_review_says_needs_review_before_export(self, vm: ReviewViewModel) -> None:
        state = _state_with_readiness("needs_review")
        assert vm.readiness_badge_text(state) == "Needs review before export"

    def test_blocked_says_blocked_do_not_export_yet(self, vm: ReviewViewModel) -> None:
        state = _state_with_readiness("blocked")
        assert vm.readiness_badge_text(state) == "Blocked: do not export yet"


# ---------------------------------------------------------------------------
# readiness_checks
# ---------------------------------------------------------------------------


class TestReadinessChecks:
    def test_empty_when_no_readiness_report(self, vm: ReviewViewModel) -> None:
        assert vm.readiness_checks(AppState()) == []

    def test_returns_check_rows_when_report_present(self, vm: ReviewViewModel) -> None:
        state = _state_with_readiness("ready")
        rows = vm.readiness_checks(state)
        assert len(rows) > 0
        assert isinstance(rows[0], ReadinessCheckRow)

    def test_check_row_fields_map_correctly(self, vm: ReviewViewModel) -> None:
        check = DjReadinessCheck(label="Playlist size", status="ready", detail="2 tracks available")
        state = AppState()
        state.last_recommendation = _make_recommendation()
        state.last_dj_readiness_report = _make_readiness("ready", [check])

        rows = vm.readiness_checks(state)
        assert len(rows) == 1
        row = rows[0]
        assert row.label == "Playlist size"
        assert row.status == "ready"
        assert row.detail == "2 tracks available"


# ---------------------------------------------------------------------------
# transition_rows
# ---------------------------------------------------------------------------


class TestTransitionRows:
    def test_empty_when_no_explanation(self, vm: ReviewViewModel) -> None:
        assert vm.transition_rows(AppState()) == []

    def test_returns_transition_rows_when_explanation_present(self, vm: ReviewViewModel) -> None:
        state = AppState()
        state.last_playlist_explanation = _make_playlist_explanation()
        rows = vm.transition_rows(state)
        assert len(rows) == 1
        assert isinstance(rows[0], TransitionRow)

    def test_transition_row_fields_map_correctly(self, vm: ReviewViewModel) -> None:
        transition = _make_transition_explanation("Track A", "Track B", final_score=0.85)
        state = AppState()
        state.last_playlist_explanation = _make_playlist_explanation([transition])

        rows = vm.transition_rows(state)
        row = rows[0]
        assert row.from_track == "Track A"
        assert row.to_track == "Track B"
        assert row.score == "0.85"

    def test_transition_row_has_warning_when_warnings_present(self, vm: ReviewViewModel) -> None:
        transition = _make_transition_explanation(warnings=["BPM jump too large"])
        state = AppState()
        state.last_playlist_explanation = _make_playlist_explanation([transition])

        rows = vm.transition_rows(state)
        assert rows[0].has_warning is True
        assert "BPM jump too large" in rows[0].warning_text

    def test_transition_row_no_warning_when_no_warnings(self, vm: ReviewViewModel) -> None:
        transition = _make_transition_explanation(warnings=[])
        state = AppState()
        state.last_playlist_explanation = _make_playlist_explanation([transition])

        rows = vm.transition_rows(state)
        assert rows[0].has_warning is False
        assert rows[0].warning_text == ""


# ---------------------------------------------------------------------------
# quality_summary
# ---------------------------------------------------------------------------


class TestQualitySummary:
    def test_dash_when_no_quality_report(self, vm: ReviewViewModel) -> None:
        assert vm.quality_summary(AppState()) == "—"

    def test_returns_string_when_quality_report_present(self, vm: ReviewViewModel) -> None:
        state = AppState()
        state.last_quality_report = _make_quality_report()
        result = vm.quality_summary(state)
        assert result != "—"
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# can_export
# ---------------------------------------------------------------------------


class TestCanExport:
    def test_false_when_no_recommendation(self, vm: ReviewViewModel) -> None:
        assert vm.can_export(AppState()) is False

    def test_false_when_readiness_blocked(self, vm: ReviewViewModel) -> None:
        state = _state_with_readiness("blocked")
        assert vm.can_export(state) is False

    def test_true_when_readiness_ready(self, vm: ReviewViewModel) -> None:
        state = _state_with_readiness("ready")
        assert vm.can_export(state) is True

    def test_true_when_readiness_needs_review(self, vm: ReviewViewModel) -> None:
        state = _state_with_readiness("needs_review")
        assert vm.can_export(state) is True


# ---------------------------------------------------------------------------
# recommendation_rows
# ---------------------------------------------------------------------------


class TestRecommendationRows:
    def test_empty_when_no_recommendation(self, vm: ReviewViewModel) -> None:
        assert vm.recommendation_rows(AppState()) == []

    def test_returns_rows_when_recommendation_present(self, vm: ReviewViewModel) -> None:
        state = AppState()
        state.last_recommendation = _make_recommendation()
        rows = vm.recommendation_rows(state)
        assert len(rows) == 1
        assert isinstance(rows[0], RecommendationRow)

    def test_recommendation_row_fields_map_correctly(self, vm: ReviewViewModel) -> None:
        track = _make_track("a.mp3", "My Track", "My Artist")
        state = AppState()
        state.last_recommendation = _make_recommendation([track])

        rows = vm.recommendation_rows(state)
        row = rows[0]
        assert row.position == 1
        assert row.title == "My Track"
        assert row.artist == "My Artist"
        assert row.bpm == "128"
        assert row.camelot_key == "8A"
        assert row.energy == "7"

    def test_position_is_one_indexed(self, vm: ReviewViewModel) -> None:
        tracks = [
            _make_track("a.mp3", "Track A", "Artist A"),
            _make_track("b.mp3", "Track B", "Artist B"),
        ]
        state = AppState()
        state.last_recommendation = _make_recommendation(tracks)

        rows = vm.recommendation_rows(state)
        assert rows[0].position == 1
        assert rows[1].position == 2

    def test_dash_for_missing_bpm(self, vm: ReviewViewModel) -> None:
        track = TrackRecord(path="x.mp3", title="No BPM", metadata_status="incomplete")
        state = AppState()
        state.last_recommendation = _make_recommendation([track])

        rows = vm.recommendation_rows(state)
        assert rows[0].bpm == "—"

    def test_dash_for_missing_key(self, vm: ReviewViewModel) -> None:
        track = TrackRecord(path="x.mp3", title="No Key", metadata_status="incomplete")
        state = AppState()
        state.last_recommendation = _make_recommendation([track])

        rows = vm.recommendation_rows(state)
        assert rows[0].camelot_key == "—"

    def test_dash_for_missing_energy(self, vm: ReviewViewModel) -> None:
        track = TrackRecord(path="x.mp3", title="No Energy", metadata_status="incomplete")
        state = AppState()
        state.last_recommendation = _make_recommendation([track])

        rows = vm.recommendation_rows(state)
        assert rows[0].energy == "—"
