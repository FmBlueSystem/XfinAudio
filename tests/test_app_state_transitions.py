"""Tests for pure AppState transition helpers."""

from __future__ import annotations

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
