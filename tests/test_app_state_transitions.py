"""Tests for pure AppState transition helpers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from xfinaudio.audio.danceability import DanceabilityProfile
from xfinaudio.audio.spectral_profile import EdgeSpectralProfile, SpectralProfile
from xfinaudio.desktop import app_state_transitions
from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.app_state_transitions import (
    apply_danceability_profile,
    apply_edge_spectral_profile,
    apply_spectral_profile,
)
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


def test_apply_danceability_profile_updates_both_track_collections_immutably() -> None:
    track = _track()
    state = AppState(scanned_records=[track], records_by_path={track.path: track})
    profile = DanceabilityProfile(
        score=0.72,
        pulse_clarity=0.8,
        tempo_confidence=0.9,
        percussive_ratio=0.6,
    )

    updated = apply_danceability_profile(state, path=track.path, profile=profile)

    assert updated is not state
    assert updated.scanned_records is not state.scanned_records
    assert updated.records_by_path is not state.records_by_path
    assert updated.scanned_records[0].danceability_profile == profile
    assert updated.records_by_path[track.path].danceability_profile == profile
    assert state.scanned_records[0].danceability_profile is None
    assert state.records_by_path[track.path].danceability_profile is None


def test_apply_edge_spectral_profile_updates_both_track_collections_immutably() -> None:
    track = _track()
    state = AppState(scanned_records=[track], records_by_path={track.path: track})
    profile = EdgeSpectralProfile(intro=_profile(), outro=_profile())

    updated = apply_edge_spectral_profile(state, path=track.path, profile=profile)

    assert updated is not state
    assert updated.scanned_records is not state.scanned_records
    assert updated.records_by_path is not state.records_by_path
    assert updated.scanned_records[0].edge_spectral_profile == profile
    assert updated.records_by_path[track.path].edge_spectral_profile == profile
    assert state.scanned_records[0].edge_spectral_profile is None
    assert state.records_by_path[track.path].edge_spectral_profile is None


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


def test_apply_library_folder_selected_sets_folder_and_resets_scan_context_immutably() -> None:
    track = _track()
    old_folder = Path("/music/old")
    new_folder = Path("/music/new")
    state = AppState(
        selected_folder=old_folder,
        scanned_records=[track],
        records_by_path={track.path: track},
        last_recommendation=object(),  # type: ignore[arg-type]
        last_playlist_explanation=object(),  # type: ignore[arg-type]
        last_quality_report=object(),  # type: ignore[arg-type]
        last_dj_readiness_report=object(),  # type: ignore[arg-type]
        last_prep_copilot_plan=object(),  # type: ignore[arg-type]
        applied_variant_name="balanced",
        playlist_removed_paths=frozenset({track.path}),
    )

    transition = getattr(app_state_transitions, "apply_library_folder_selected", None)
    assert callable(transition)
    updated = transition(state, new_folder)

    assert updated is not state
    assert updated.selected_folder == new_folder
    assert updated.scanned_records == []
    assert updated.records_by_path == {}
    assert updated.last_recommendation is None
    assert updated.last_playlist_explanation is None
    assert updated.last_quality_report is None
    assert updated.last_dj_readiness_report is None
    assert updated.last_prep_copilot_plan is None
    assert updated.applied_variant_name is None
    assert updated.playlist_removed_paths == frozenset()
    assert state.selected_folder == old_folder
    assert state.scanned_records == [track]
    assert state.records_by_path == {track.path: track}


def test_apply_library_records_loaded_replaces_records_and_lookup_immutably() -> None:
    old_track = _track("/music/old.flac")
    first = _track("/music/a.flac")
    second = _track("/music/b.flac")
    external_records = [first, second]
    state = AppState(scanned_records=[old_track], records_by_path={old_track.path: old_track})

    transition = getattr(app_state_transitions, "apply_library_records_loaded", None)
    assert callable(transition)
    updated = transition(state, external_records)

    assert updated is not state
    assert updated.scanned_records == [first, second]
    assert updated.scanned_records is not external_records
    assert updated.records_by_path == {first.path: first, second.path: second}
    assert state.scanned_records == [old_track]
    assert state.records_by_path == {old_track.path: old_track}


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


# ---------------------------------------------------------------------------
# Hand edits made on the Export screen.
#
# The crate is written from state.last_recommendation, so an edit that only
# changed the table would export the untouched original.
# ---------------------------------------------------------------------------


def _export_state(paths: list[str]):
    from xfinaudio.desktop.app_state import AppState
    from xfinaudio.library.models import TrackRecord
    from xfinaudio.recommendation.playlist_service import recommend_playlist

    tracks = [
        TrackRecord(
            path=path,
            title=path.rsplit("/", maxsplit=1)[-1],
            bpm=120.0,
            camelot_key="8A",
            energy_level=6,
            metadata_status="complete",
        )
        for path in paths
    ]
    return AppState(last_recommendation=recommend_playlist(tracks, "same_energy"))


def test_apply_export_track_order_reorders_the_exported_recommendation() -> None:
    from xfinaudio.desktop.app_state_transitions import apply_export_track_order

    state = _export_state(["/a.flac", "/b.flac", "/c.flac"])
    assert state.last_recommendation is not None
    flipped = list(reversed([track.path for track in state.last_recommendation.ordered_tracks]))

    result = apply_export_track_order(state, flipped)

    assert result.last_recommendation is not None
    assert [track.path for track in result.last_recommendation.ordered_tracks] == flipped


def test_apply_export_track_order_rescores_rather_than_carrying_stale_seams() -> None:
    from xfinaudio.desktop.app_state_transitions import apply_export_track_order

    state = _export_state(["/a.flac", "/b.flac", "/c.flac"])
    assert state.last_recommendation is not None
    flipped = list(reversed([track.path for track in state.last_recommendation.ordered_tracks]))

    result = apply_export_track_order(state, flipped)

    assert result.last_recommendation is not None
    scores = result.last_recommendation.transition_scores
    assert [score.left_path for score in scores] == flipped[:-1]
    assert [score.right_path for score in scores] == flipped[1:]


def test_apply_export_track_removal_drops_the_track() -> None:
    from xfinaudio.desktop.app_state_transitions import apply_export_track_removal

    state = _export_state(["/a.flac", "/b.flac", "/c.flac"])
    assert state.last_recommendation is not None
    doomed = state.last_recommendation.ordered_tracks[1].path

    result = apply_export_track_removal(state, doomed)

    assert result.last_recommendation is not None
    remaining = [track.path for track in result.last_recommendation.ordered_tracks]
    assert doomed not in remaining
    assert len(remaining) == 2


def test_export_edits_are_inert_without_a_recommendation() -> None:
    """Nothing to edit is not an error -- the screen may render before one exists."""
    from xfinaudio.desktop.app_state import AppState
    from xfinaudio.desktop.app_state_transitions import apply_export_track_order, apply_export_track_removal

    empty = AppState()

    assert apply_export_track_order(empty, ["/a.flac"]) is empty
    assert apply_export_track_removal(empty, "/a.flac") is empty


# ---------------------------------------------------------------------------
# Removing a track has to move the panels that describe the playlist.
#
# The Review screen's track table filtered `playlist_removed_paths`, but the
# transition table, the readiness checks and the quality summary all read
# reports built once when the recommendation was generated and never rebuilt.
# Remove a track and the top of the screen dropped a row while the bottom still
# described fifteen.
# ---------------------------------------------------------------------------


def _reviewed_state(paths: list[str]):
    from xfinaudio.desktop.app_state import AppState
    from xfinaudio.exporting.explainability import build_playlist_explanation
    from xfinaudio.library.models import TrackRecord
    from xfinaudio.quality.dj_readiness import build_dj_readiness_report
    from xfinaudio.quality.recommendation_quality import build_quality_report
    from xfinaudio.recommendation.playlist_service import recommend_playlist

    tracks = [
        TrackRecord(
            path=path,
            title=path.rsplit("/", maxsplit=1)[-1],
            bpm=120.0 + index * 0.5,
            camelot_key="8A",
            energy_level=6,
            metadata_status="complete",
        )
        for index, path in enumerate(paths)
    ]
    recommendation = recommend_playlist(tracks, "same_energy")
    quality = build_quality_report(recommendation)
    return AppState(
        last_recommendation=recommendation,
        last_playlist_explanation=build_playlist_explanation(recommendation),
        last_quality_report=quality,
        last_dj_readiness_report=build_dj_readiness_report(recommendation, quality),
    )


def test_removing_a_track_rebuilds_the_transition_explanation() -> None:
    from xfinaudio.desktop.app_state_transitions import apply_playlist_track_removed

    state = _reviewed_state(["/a.flac", "/b.flac", "/c.flac", "/d.flac"])
    assert state.last_playlist_explanation is not None
    assert state.last_recommendation is not None
    before = len(state.last_playlist_explanation.transitions)
    doomed = state.last_recommendation.ordered_tracks[1].path

    result = apply_playlist_track_removed(state, doomed)

    assert result.last_playlist_explanation is not None
    assert len(result.last_playlist_explanation.transitions) == before - 1
    named = {t.left.path for t in result.last_playlist_explanation.transitions} | {
        t.right.path for t in result.last_playlist_explanation.transitions
    }
    assert doomed not in named


def test_removing_a_track_rebuilds_the_quality_summary() -> None:
    from xfinaudio.desktop.app_state_transitions import apply_playlist_track_removed

    state = _reviewed_state(["/a.flac", "/b.flac", "/c.flac", "/d.flac"])
    assert state.last_quality_report is not None
    assert state.last_recommendation is not None
    before = state.last_quality_report.transition_count
    doomed = state.last_recommendation.ordered_tracks[1].path

    result = apply_playlist_track_removed(state, doomed)

    assert result.last_quality_report is not None
    assert result.last_quality_report.transition_count == before - 1


def test_removing_a_track_rebuilds_the_readiness_report() -> None:
    """The playlist-size check counted the tracks it was built with."""
    from xfinaudio.desktop.app_state_transitions import apply_playlist_track_removed

    state = _reviewed_state(["/a.flac", "/b.flac", "/c.flac", "/d.flac"])
    assert state.last_recommendation is not None
    doomed = state.last_recommendation.ordered_tracks[1].path

    result = apply_playlist_track_removed(state, doomed)

    assert result.last_dj_readiness_report is not None
    assert result.last_dj_readiness_report is not state.last_dj_readiness_report
    details = " ".join(check.detail for check in result.last_dj_readiness_report.checks)
    assert "4 track" not in details, f"still describing the pre-removal playlist: {details}"


def test_a_backfilled_removal_also_rebuilds_the_panels() -> None:
    from xfinaudio.desktop.app_state_transitions import apply_playlist_track_replaced
    from xfinaudio.recommendation.playlist_service import recommendation_without_paths

    state = _reviewed_state(["/a.flac", "/b.flac", "/c.flac", "/d.flac"])
    assert state.last_recommendation is not None
    doomed = state.last_recommendation.ordered_tracks[1].path
    backfilled = recommendation_without_paths(state.last_recommendation, frozenset({doomed}))

    result = apply_playlist_track_replaced(state, path=doomed, recommendation=backfilled)

    assert result.last_playlist_explanation is not None
    assert len(result.last_playlist_explanation.transitions) == len(backfilled.ordered_tracks) - 1


def test_restoring_a_track_rebuilds_the_panels_too() -> None:
    from xfinaudio.desktop.app_state_transitions import apply_playlist_track_removed, apply_playlist_track_restored

    state = _reviewed_state(["/a.flac", "/b.flac", "/c.flac", "/d.flac"])
    original = state.last_recommendation
    assert original is not None
    doomed = original.ordered_tracks[1].path

    removed = apply_playlist_track_removed(state, doomed)
    restored = apply_playlist_track_restored(removed, doomed, original)

    assert restored.last_playlist_explanation is not None
    assert len(restored.last_playlist_explanation.transitions) == len(original.ordered_tracks) - 1
