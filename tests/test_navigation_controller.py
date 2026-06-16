"""Tests for NavigationController DJ flow navigation rules."""

from __future__ import annotations

import pytest

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.navigation_controller import NavigationController
from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.dj_readiness import DjReadinessReport
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.strategies import default_strategy_registry

# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------


def _make_track(path: str = "/music/track.mp3") -> TrackRecord:
    return TrackRecord(path=path)


def _make_recommendation() -> PlaylistRecommendation:
    # Include a track so the recommendation is realistically exportable; an empty playlist is never
    # a valid export target under the unified export gate.
    return PlaylistRecommendation(
        ordered_tracks=[_make_track("/music/track.mp3")],
        transition_scores=[],
        strategy=default_strategy_registry().get("build"),
        warnings=[],
        applied_controls={},
        optimizer="test",
        total_score=0.0,
    )


def _make_readiness(status: str, blocker_count: int = 0) -> DjReadinessReport:
    return DjReadinessReport(
        status=status,  # type: ignore[arg-type]
        summary="test",
        checks=[],
        blocker_count=blocker_count,
        review_count=0,
    )


def _ready_readiness() -> DjReadinessReport:
    return _make_readiness("ready", blocker_count=0)


def _blocked_readiness() -> DjReadinessReport:
    return _make_readiness("blocked", blocker_count=1)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ctrl() -> NavigationController:
    return NavigationController()


@pytest.fixture
def empty_state() -> AppState:
    return AppState()


@pytest.fixture
def state_with_tracks() -> AppState:
    s = AppState()
    return s.with_scanned_records([_make_track()])


@pytest.fixture
def state_scanning() -> AppState:
    s = AppState(is_scanning=True)
    return s.with_scanned_records([_make_track()])


@pytest.fixture
def state_with_recommendation() -> AppState:
    return AppState(last_recommendation=_make_recommendation())


@pytest.fixture
def state_with_ready_readiness() -> AppState:
    return AppState(
        last_recommendation=_make_recommendation(),
        last_dj_readiness_report=_ready_readiness(),
    )


@pytest.fixture
def state_with_blocked_readiness() -> AppState:
    return AppState(
        last_recommendation=_make_recommendation(),
        last_dj_readiness_report=_blocked_readiness(),
    )


@pytest.fixture
def state_recommending() -> AppState:
    return AppState(last_recommendation=_make_recommendation(), is_recommending=True)


# ---------------------------------------------------------------------------
# can_go_to — library and metadata always accessible
# ---------------------------------------------------------------------------


def test_can_go_to_library_always_true(ctrl, empty_state):
    assert ctrl.can_go_to("library", empty_state) is True


def test_can_go_to_library_always_true_with_tracks(ctrl, state_with_tracks):
    assert ctrl.can_go_to("library", state_with_tracks) is True


def test_can_go_to_metadata_always_true(ctrl, empty_state):
    assert ctrl.can_go_to("metadata", empty_state) is True


def test_can_go_to_metadata_always_true_with_tracks(ctrl, state_with_tracks):
    assert ctrl.can_go_to("metadata", state_with_tracks) is True


# ---------------------------------------------------------------------------
# can_go_to — build
# ---------------------------------------------------------------------------


def test_can_go_to_build_without_tracks_returns_false(ctrl, empty_state):
    assert ctrl.can_go_to("build", empty_state) is False


def test_can_go_to_build_with_tracks_returns_true(ctrl, state_with_tracks):
    assert ctrl.can_go_to("build", state_with_tracks) is True


def test_can_go_to_build_while_scanning_returns_false(ctrl, state_scanning):
    assert ctrl.can_go_to("build", state_scanning) is False


# ---------------------------------------------------------------------------
# can_go_to — review
# ---------------------------------------------------------------------------


def test_can_go_to_review_without_recommendation_returns_false(ctrl, empty_state):
    assert ctrl.can_go_to("review", empty_state) is False


def test_can_go_to_review_with_recommendation_returns_true(ctrl, state_with_recommendation):
    assert ctrl.can_go_to("review", state_with_recommendation) is True


def test_can_go_to_review_while_recommending_returns_false(ctrl, state_recommending):
    assert ctrl.can_go_to("review", state_recommending) is False


# ---------------------------------------------------------------------------
# can_go_to — export
# ---------------------------------------------------------------------------


def test_can_go_to_export_without_readiness_returns_true(ctrl, state_with_recommendation):
    # Unified export gate: a recommendation with no readiness report is exportable (no info → no
    # block), matching the Review and Export view models. This removes the sidebar dead-end.
    assert ctrl.can_go_to("export", state_with_recommendation) is True


def test_can_go_to_export_without_recommendation_returns_false(ctrl, empty_state):
    assert ctrl.can_go_to("export", empty_state) is False


def test_can_go_to_export_with_ready_readiness_returns_true(ctrl, state_with_ready_readiness):
    assert ctrl.can_go_to("export", state_with_ready_readiness) is True


def test_can_go_to_export_with_blocked_readiness_returns_false(ctrl, state_with_blocked_readiness):
    assert ctrl.can_go_to("export", state_with_blocked_readiness) is False


def test_can_go_to_export_while_recommending_returns_false(ctrl, state_recommending):
    s = state_recommending
    s.last_dj_readiness_report = _ready_readiness()
    assert ctrl.can_go_to("export", s) is False


# ---------------------------------------------------------------------------
# go_to
# ---------------------------------------------------------------------------


def test_go_to_invalid_returns_same_state(ctrl, empty_state):
    result = ctrl.go_to("build", empty_state)
    assert result is empty_state


def test_go_to_library_from_empty_state(ctrl, empty_state):
    result = ctrl.go_to("library", empty_state)
    assert result.current_screen == "library"
    assert result is not empty_state


def test_go_to_build_with_tracks(ctrl, state_with_tracks):
    result = ctrl.go_to("build", state_with_tracks)
    assert result.current_screen == "build"


def test_go_to_build_without_tracks_no_change(ctrl, empty_state):
    result = ctrl.go_to("build", empty_state)
    assert result.current_screen == "library"


# ---------------------------------------------------------------------------
# next_screen
# ---------------------------------------------------------------------------


def test_next_screen_library_with_tracks_returns_build(ctrl, state_with_tracks):
    s = state_with_tracks.with_screen("library")
    assert ctrl.next_screen(s) == "build"


def test_next_screen_library_without_tracks_returns_none(ctrl, empty_state):
    assert ctrl.next_screen(empty_state) is None


def test_next_screen_export_returns_none(ctrl, state_with_ready_readiness):
    s = state_with_ready_readiness.with_screen("export")
    assert ctrl.next_screen(s) is None


def test_next_screen_metadata_returns_none(ctrl, empty_state):
    s = empty_state.with_screen("metadata")
    assert ctrl.next_screen(s) is None


def test_next_screen_build_with_recommendation_returns_review(ctrl, state_with_recommendation):
    s = state_with_recommendation.with_scanned_records([_make_track()]).with_screen("build")
    assert ctrl.next_screen(s) == "review"


def test_next_screen_review_with_ready_readiness_returns_export(ctrl, state_with_ready_readiness):
    s = state_with_ready_readiness.with_screen("review")
    assert ctrl.next_screen(s) == "export"


# ---------------------------------------------------------------------------
# back_screen
# ---------------------------------------------------------------------------


def test_back_screen_build_returns_library(ctrl, state_with_tracks):
    s = state_with_tracks.with_screen("build")
    assert ctrl.back_screen(s) == "library"


def test_back_screen_library_returns_none(ctrl, empty_state):
    s = empty_state.with_screen("library")
    assert ctrl.back_screen(s) is None


def test_back_screen_while_scanning_returns_none(ctrl, state_scanning):
    s = state_scanning.with_screen("build")
    assert ctrl.back_screen(s) is None


def test_back_screen_while_recommending_returns_none(ctrl, state_recommending):
    s = state_recommending.with_screen("review")
    assert ctrl.back_screen(s) is None


def test_back_screen_review_returns_build(ctrl, state_with_recommendation):
    s = state_with_recommendation.with_screen("review")
    assert ctrl.back_screen(s) == "build"


def test_back_screen_export_returns_review(ctrl, state_with_ready_readiness):
    s = state_with_ready_readiness.with_screen("export")
    assert ctrl.back_screen(s) == "review"


def test_back_screen_metadata_returns_none(ctrl, empty_state):
    s = empty_state.with_screen("metadata")
    assert ctrl.back_screen(s) is None


# ---------------------------------------------------------------------------
# can_go_to — unknown screen
# ---------------------------------------------------------------------------


def test_can_go_to_unknown_screen_returns_false():
    ctrl = NavigationController()
    state = AppState()
    assert ctrl.can_go_to("nonexistent", state) is False


# ---------------------------------------------------------------------------
# R3 — unified export gate parity across nav + view models
# ---------------------------------------------------------------------------


def _recommendation_with_tracks() -> PlaylistRecommendation:
    return _make_recommendation().model_copy(update={"ordered_tracks": [_make_track("/music/a.mp3")]})


def _export_gate_triplet(state):
    from xfinaudio.desktop.export_view_model import ExportViewModel
    from xfinaudio.desktop.review_view_model import ReviewViewModel

    nav = NavigationController().can_go_to("export", state)
    review = ReviewViewModel().can_export(state)
    export = ExportViewModel().export_enabled(state)
    return nav, review, export


def test_export_gate_agrees_when_recommendation_but_no_report() -> None:
    # The dead-end: nav used to require a report while the view models allowed export.
    state = AppState(last_recommendation=_recommendation_with_tracks())
    nav, review, export = _export_gate_triplet(state)
    assert nav == review == export is True


def test_export_gate_agrees_when_ready() -> None:
    state = AppState(last_recommendation=_recommendation_with_tracks(), last_dj_readiness_report=_ready_readiness())
    nav, review, export = _export_gate_triplet(state)
    assert nav == review == export is True


def test_export_gate_agrees_when_blocked() -> None:
    state = AppState(last_recommendation=_recommendation_with_tracks(), last_dj_readiness_report=_blocked_readiness())
    nav, review, export = _export_gate_triplet(state)
    assert nav == review == export is False


def test_export_gate_agrees_when_all_tracks_removed() -> None:
    rec = _recommendation_with_tracks()
    state = AppState(
        last_recommendation=rec,
        last_dj_readiness_report=_ready_readiness(),
        playlist_removed_paths=frozenset({"/music/a.mp3"}),
    )
    nav, review, export = _export_gate_triplet(state)
    assert nav == review == export is False
