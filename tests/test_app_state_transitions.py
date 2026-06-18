"""Tests for pure AppState transition helpers."""

from __future__ import annotations

from xfinaudio.audio.spectral_profile import SpectralProfile
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
