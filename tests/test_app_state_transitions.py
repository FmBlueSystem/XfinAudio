"""Tests for pure AppState transition helpers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from xfinaudio.audio.spectral_profile import SpectralProfile
from xfinaudio.desktop import app_state_transitions
from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.app_state_transitions import apply_spectral_profile
from xfinaudio.library.models import TrackRecord


def _track(path: str = "/music/a.flac") -> TrackRecord:
    return TrackRecord(path=path, title="A")


def _profile() -> SpectralProfile:
    return SpectralProfile(
        red_ratio=1.0,
        green_ratio=0.0,
        blue_ratio=0.0,
        dominant_color="RED",
    )


def test_apply_spectral_profile_returns_new_state_without_mutating_original() -> None:
    track = _track()
    state = AppState(scanned_records=[track], records_by_path={track.path: track})
    profile = _profile()

    updated = apply_spectral_profile(state, path=track.path, profile=profile)

    assert updated is not state
    assert updated.scanned_records is not state.scanned_records
    assert updated.records_by_path is not state.records_by_path
    assert updated.scanned_records[0] is not track
    assert updated.scanned_records[0].spectral_profile == profile
    assert updated.records_by_path[track.path].spectral_profile == profile
    assert state.scanned_records[0].spectral_profile is None
    assert state.records_by_path[track.path].spectral_profile is None


def test_apply_spectral_profile_updates_scanned_records_and_records_by_path_consistently() -> None:
    track = _track()
    state = AppState(scanned_records=[track], records_by_path={track.path: track})
    profile = _profile()

    updated = apply_spectral_profile(state, path=track.path, profile=profile)

    assert updated.scanned_records[0] == updated.records_by_path[track.path]
    assert updated.scanned_records[0].path == track.path


def test_apply_spectral_profile_leaves_unknown_path_unchanged_but_copied() -> None:
    track = _track()
    state = AppState(scanned_records=[track], records_by_path={track.path: track})

    updated = apply_spectral_profile(state, path="/music/missing.flac", profile=_profile())

    assert updated is not state
    assert updated.scanned_records is not state.scanned_records
    assert updated.records_by_path is not state.records_by_path
    assert updated.scanned_records == state.scanned_records
    assert updated.records_by_path == state.records_by_path


def test_apply_recommendation_completion_returns_new_state_without_mutating_original() -> None:
    previous_recommendation = object()
    previous_explanation = object()
    previous_quality_report = object()
    completed_recommendation = object()
    completed_explanation = object()
    completed_quality_report = object()
    state = AppState(
        last_recommendation=previous_recommendation,  # type: ignore[arg-type]
        last_playlist_explanation=previous_explanation,  # type: ignore[arg-type]
        last_quality_report=previous_quality_report,  # type: ignore[arg-type]
        playlist_removed_paths=frozenset({"/music/removed.flac"}),
        applied_variant_name="balanced",
    )
    result = SimpleNamespace(
        recommendation=completed_recommendation,
        explanation=completed_explanation,
        quality_report=completed_quality_report,
    )

    transition = getattr(app_state_transitions, "apply_recommendation_completion", None)
    assert callable(transition)
    updated = transition(state, result)

    assert updated is not state
    assert updated.last_recommendation is completed_recommendation
    assert updated.last_playlist_explanation is completed_explanation
    assert updated.last_quality_report is completed_quality_report
    assert updated.playlist_removed_paths == frozenset()
    assert updated.applied_variant_name is None
    assert state.last_recommendation is previous_recommendation
    assert state.last_playlist_explanation is previous_explanation
    assert state.last_quality_report is previous_quality_report
    assert state.playlist_removed_paths == frozenset({"/music/removed.flac"})
    assert state.applied_variant_name == "balanced"


def test_apply_scan_context_reset_clears_scan_and_recommendation_state_immutably() -> None:
    track = _track()
    state = AppState(
        selected_folder=Path("/music/old"),
        scanned_records=[track],
        records_by_path={track.path: track},
        last_recommendation=object(),  # type: ignore[arg-type]
        last_playlist_explanation=object(),  # type: ignore[arg-type]
        last_quality_report=object(),  # type: ignore[arg-type]
        last_dj_readiness_report=object(),  # type: ignore[arg-type]
        last_prep_copilot_plan=object(),  # type: ignore[arg-type]
        applied_variant_name="balanced",
        playlist_removed_paths=frozenset({track.path}),
        excluded_paths=frozenset({"/music/excluded.flac"}),
        locked_paths=frozenset({"/music/locked.flac"}),
    )

    transition = getattr(app_state_transitions, "apply_scan_context_reset", None)
    assert callable(transition)
    updated = transition(state)

    assert updated is not state
    assert updated.scanned_records == []
    assert updated.records_by_path == {}
    assert updated.last_recommendation is None
    assert updated.last_playlist_explanation is None
    assert updated.last_quality_report is None
    assert updated.last_dj_readiness_report is None
    assert updated.last_prep_copilot_plan is None
    assert updated.applied_variant_name is None
    assert updated.playlist_removed_paths == frozenset()
    assert updated.excluded_paths == state.excluded_paths
    assert updated.locked_paths == state.locked_paths
    assert state.scanned_records == [track]
    assert state.records_by_path == {track.path: track}
    assert state.applied_variant_name == "balanced"
    assert state.playlist_removed_paths == frozenset({track.path})


def test_apply_playlist_track_removed_returns_new_state_without_mutating_original() -> None:
    state = AppState(playlist_removed_paths=frozenset({"/music/a.flac"}))

    transition = getattr(app_state_transitions, "apply_playlist_track_removed", None)
    assert callable(transition)
    updated = transition(state, "/music/b.flac")

    assert updated is not state
    assert updated.playlist_removed_paths == frozenset({"/music/a.flac", "/music/b.flac"})
    assert state.playlist_removed_paths == frozenset({"/music/a.flac"})


def test_apply_playlist_track_restored_returns_new_state_without_mutating_original() -> None:
    state = AppState(playlist_removed_paths=frozenset({"/music/a.flac", "/music/b.flac"}))

    transition = getattr(app_state_transitions, "apply_playlist_track_restored", None)
    assert callable(transition)
    updated = transition(state, "/music/b.flac")

    assert updated is not state
    assert updated.playlist_removed_paths == frozenset({"/music/a.flac"})
    assert state.playlist_removed_paths == frozenset({"/music/a.flac", "/music/b.flac"})


def test_apply_prep_copilot_variant_returns_new_state_and_clears_removed_paths() -> None:
    previous_recommendation = object()
    previous_explanation = object()
    previous_quality_report = object()
    previous_readiness = object()
    recommendation = object()
    explanation = object()
    quality_report = object()
    readiness = object()
    state = AppState(
        last_recommendation=previous_recommendation,  # type: ignore[arg-type]
        last_playlist_explanation=previous_explanation,  # type: ignore[arg-type]
        last_quality_report=previous_quality_report,  # type: ignore[arg-type]
        last_dj_readiness_report=previous_readiness,  # type: ignore[arg-type]
        playlist_removed_paths=frozenset({"/music/removed.flac"}),
        applied_variant_name="safe",
    )
    payload = SimpleNamespace(
        recommendation=recommendation,
        explanation=explanation,
        quality_report=quality_report,
        readiness_report=readiness,
        variant_name="balanced",
    )

    transition = getattr(app_state_transitions, "apply_prep_copilot_variant", None)
    assert callable(transition)
    updated = transition(state, payload)

    assert updated is not state
    assert updated.last_recommendation is recommendation
    assert updated.last_playlist_explanation is explanation
    assert updated.last_quality_report is quality_report
    assert updated.last_dj_readiness_report is readiness
    assert updated.playlist_removed_paths == frozenset()
    assert updated.applied_variant_name == "balanced"
    assert state.last_recommendation is previous_recommendation
    assert state.last_playlist_explanation is previous_explanation
    assert state.last_quality_report is previous_quality_report
    assert state.last_dj_readiness_report is previous_readiness
    assert state.playlist_removed_paths == frozenset({"/music/removed.flac"})
    assert state.applied_variant_name == "safe"


def test_apply_tracks_excluded_returns_new_state_without_mutating_original() -> None:
    state = AppState(excluded_paths=frozenset({"/music/a.flac"}))

    transition = getattr(app_state_transitions, "apply_tracks_excluded", None)
    assert callable(transition)
    updated = transition(state, ["/music/b.flac", "/music/c.flac"])

    assert updated is not state
    assert updated.excluded_paths == frozenset({"/music/a.flac", "/music/b.flac", "/music/c.flac"})
    assert state.excluded_paths == frozenset({"/music/a.flac"})


def test_apply_tracks_locked_returns_new_state_without_mutating_original() -> None:
    state = AppState(locked_paths=frozenset({"/music/a.flac"}))

    transition = getattr(app_state_transitions, "apply_tracks_locked", None)
    assert callable(transition)
    updated = transition(state, ["/music/b.flac"])

    assert updated is not state
    assert updated.locked_paths == frozenset({"/music/a.flac", "/music/b.flac"})
    assert state.locked_paths == frozenset({"/music/a.flac"})


def test_apply_track_constraints_cleared_returns_new_state_without_mutating_original() -> None:
    state = AppState(
        excluded_paths=frozenset({"/music/excluded.flac"}),
        locked_paths=frozenset({"/music/locked.flac"}),
    )

    transition = getattr(app_state_transitions, "apply_track_constraints_cleared", None)
    assert callable(transition)
    updated = transition(state)

    assert updated is not state
    assert updated.excluded_paths == frozenset()
    assert updated.locked_paths == frozenset()
    assert state.excluded_paths == frozenset({"/music/excluded.flac"})
    assert state.locked_paths == frozenset({"/music/locked.flac"})


def test_apply_prep_copilot_plan_generated_returns_new_state_without_mutating_original() -> None:
    plan = object()
    state = AppState(last_prep_copilot_plan=None)

    transition = getattr(app_state_transitions, "apply_prep_copilot_plan_generated", None)
    assert callable(transition)
    updated = transition(state, plan)  # type: ignore[arg-type]

    assert updated is not state
    assert updated.last_prep_copilot_plan is plan
    assert state.last_prep_copilot_plan is None


def test_apply_prep_copilot_plan_cleared_returns_new_state_without_mutating_original() -> None:
    plan = object()
    state = AppState(last_prep_copilot_plan=plan)  # type: ignore[arg-type]

    transition = getattr(app_state_transitions, "apply_prep_copilot_plan_cleared", None)
    assert callable(transition)
    updated = transition(state)

    assert updated is not state
    assert updated.last_prep_copilot_plan is None
    assert state.last_prep_copilot_plan is plan


def test_apply_saved_playlist_export_recommendation_returns_new_state_without_mutating_original() -> None:
    previous_recommendation = object()
    replacement = object()
    state = AppState(last_recommendation=previous_recommendation)  # type: ignore[arg-type]

    transition = getattr(app_state_transitions, "apply_saved_playlist_export_recommendation", None)
    assert callable(transition)
    updated = transition(state, replacement)  # type: ignore[arg-type]

    assert updated is not state
    assert updated.last_recommendation is replacement
    assert state.last_recommendation is previous_recommendation
