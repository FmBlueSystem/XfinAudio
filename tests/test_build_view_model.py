"""Tests for BuildViewModel — build screen data transformation."""

from __future__ import annotations

import pytest

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.build_view_model import BuildViewModel, CopilotVariantRow, StrategyOption
from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.dj_readiness import DjReadinessReport
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.prep_copilot import (
    DJSetIntent,
    PrepCopilotPlan,
    PrepCopilotVariant,
)
from xfinaudio.recommendation.scoring import ScoringWeights
from xfinaudio.recommendation.strategies import PlaylistStrategy

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _complete_track(path: str) -> TrackRecord:
    return TrackRecord(
        path=path,
        bpm=128.0,
        camelot_key="8A",
        energy_level=7,
        metadata_status="complete",
    )


def _minimal_readiness(status: str = "ready") -> DjReadinessReport:
    return DjReadinessReport(
        status=status,  # type: ignore[arg-type]
        summary="Ready",
        checks=[],
        blocker_count=0,
        review_count=0,
    )


def _minimal_recommendation(tracks: list[TrackRecord]) -> PlaylistRecommendation:
    return PlaylistRecommendation(
        ordered_tracks=tracks,
        transition_scores=[],
        strategy=PlaylistStrategy(
            name="harmonic_journey",
            display_name="Harmonic Journey",
            description="Test strategy",
            weights=ScoringWeights(),
        ),
        warnings=[],
        applied_controls={},
        optimizer="test",
        total_score=0.0,
    )


def _minimal_variant(name: str, tracks: list[TrackRecord], blockers: int = 0) -> PrepCopilotVariant:
    readiness_status = "blocked" if blockers > 0 else "ready"
    return PrepCopilotVariant(
        name=name,  # type: ignore[arg-type]
        description=f"Description for {name}",
        recommendation=_minimal_recommendation(tracks),
        readiness=DjReadinessReport(
            status=readiness_status,  # type: ignore[arg-type]
            summary="Test",
            checks=[],
            blocker_count=blockers,
            review_count=0,
        ),
        warnings=[],
        blockers=["block!"] * blockers,
    )


def _minimal_plan(tracks: list[TrackRecord]) -> PrepCopilotPlan:
    intent = DJSetIntent(name="Test Set")
    variants = [
        _minimal_variant("safe", tracks),
        _minimal_variant("balanced", tracks),
        _minimal_variant("adventurous", tracks),
    ]
    return PrepCopilotPlan(intent=intent, variants=variants)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def vm() -> BuildViewModel:
    return BuildViewModel()


@pytest.fixture()
def tracks() -> list[TrackRecord]:
    return [_complete_track("/a.flac"), _complete_track("/b.flac")]


@pytest.fixture()
def state_with_tracks(tracks: list[TrackRecord]) -> AppState:
    return AppState(scanned_records=tracks)


@pytest.fixture()
def state_is_recommending(tracks: list[TrackRecord]) -> AppState:
    s = AppState(scanned_records=tracks)
    s.is_recommending = True
    return s


@pytest.fixture()
def state_is_scanning(tracks: list[TrackRecord]) -> AppState:
    s = AppState(scanned_records=tracks)
    s.is_scanning = True
    return s


@pytest.fixture()
def state_with_plan(tracks: list[TrackRecord]) -> AppState:
    return AppState(scanned_records=tracks, last_prep_copilot_plan=_minimal_plan(tracks))


@pytest.fixture()
def state_applied_safe(tracks: list[TrackRecord]) -> AppState:
    return AppState(scanned_records=tracks, applied_variant_name="safe")


@pytest.fixture()
def state_applied_adventurous(tracks: list[TrackRecord]) -> AppState:
    return AppState(scanned_records=tracks, applied_variant_name="adventurous")


@pytest.fixture()
def state_with_recommendation(tracks: list[TrackRecord]) -> AppState:
    return AppState(
        scanned_records=tracks,
        last_recommendation=_minimal_recommendation(tracks),
    )


# ---------------------------------------------------------------------------
# available_strategies
# ---------------------------------------------------------------------------


def test_available_strategies_returns_nonempty_list(vm: BuildViewModel) -> None:
    result = vm.available_strategies()
    assert len(result) > 0


def test_available_strategies_includes_harmonic_journey(vm: BuildViewModel) -> None:
    names = [opt.name for opt in vm.available_strategies()]
    assert "harmonic_journey" in names


def test_available_strategies_each_item_has_nonempty_strings(vm: BuildViewModel) -> None:
    for opt in vm.available_strategies():
        assert isinstance(opt, StrategyOption)
        assert opt.name
        assert opt.display_name
        assert opt.description


# ---------------------------------------------------------------------------
# recommend_button_enabled
# ---------------------------------------------------------------------------


def test_recommend_button_disabled_without_tracks(vm: BuildViewModel) -> None:
    assert vm.recommend_button_enabled(AppState()) is False


def test_recommend_button_enabled_with_tracks(vm: BuildViewModel, state_with_tracks: AppState) -> None:
    assert vm.recommend_button_enabled(state_with_tracks) is True


def test_recommend_button_disabled_while_recommending(vm: BuildViewModel, state_is_recommending: AppState) -> None:
    assert vm.recommend_button_enabled(state_is_recommending) is False


def test_recommend_button_disabled_while_scanning(vm: BuildViewModel, state_is_scanning: AppState) -> None:
    assert vm.recommend_button_enabled(state_is_scanning) is False


# ---------------------------------------------------------------------------
# copilot_button_enabled
# ---------------------------------------------------------------------------


def test_copilot_button_disabled_without_tracks(vm: BuildViewModel) -> None:
    assert vm.copilot_button_enabled(AppState()) is False


def test_copilot_button_enabled_with_tracks(vm: BuildViewModel, state_with_tracks: AppState) -> None:
    assert vm.copilot_button_enabled(state_with_tracks) is True


# ---------------------------------------------------------------------------
# copilot_variants_for_display
# ---------------------------------------------------------------------------


def test_copilot_variants_empty_without_plan(vm: BuildViewModel) -> None:
    assert vm.copilot_variants_for_display(AppState()) == []


def test_copilot_variants_returns_three_rows(vm: BuildViewModel, state_with_plan: AppState) -> None:
    result = vm.copilot_variants_for_display(state_with_plan)
    assert len(result) == 3


def test_copilot_variants_each_row_has_valid_fields(vm: BuildViewModel, state_with_plan: AppState) -> None:
    for row in vm.copilot_variants_for_display(state_with_plan):
        assert isinstance(row, CopilotVariantRow)
        assert isinstance(row.index, int)
        assert row.name
        assert row.description


# ---------------------------------------------------------------------------
# applied_variant_label
# ---------------------------------------------------------------------------


def test_applied_variant_label_empty_when_none(vm: BuildViewModel) -> None:
    assert vm.applied_variant_label(AppState()) == ""


def test_applied_variant_label_safe(vm: BuildViewModel, state_applied_safe: AppState) -> None:
    assert vm.applied_variant_label(state_applied_safe) == "Active: Safe"


def test_applied_variant_label_adventurous(vm: BuildViewModel, state_applied_adventurous: AppState) -> None:
    assert vm.applied_variant_label(state_applied_adventurous) == "Active: Adventurous"


# ---------------------------------------------------------------------------
# can_proceed
# ---------------------------------------------------------------------------


def test_can_proceed_false_without_recommendation(vm: BuildViewModel) -> None:
    assert vm.can_proceed(AppState()) is False


def test_can_proceed_true_with_recommendation(vm: BuildViewModel, state_with_recommendation: AppState) -> None:
    assert vm.can_proceed(state_with_recommendation) is True
