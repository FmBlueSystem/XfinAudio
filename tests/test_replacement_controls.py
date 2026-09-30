"""Backfill retains the DJ policy using synthetic metadata only."""

from unittest.mock import Mock

import pytest

from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import recommend_playlist, recommendation_with_replacement


def _track(path: str, *, genre: str = "House", energy: int = 5) -> TrackRecord:
    return TrackRecord(
        path=path, bpm=120, camelot_key="8A", energy_level=energy, genre=genre, metadata_status="complete"
    )


def test_replacement_helper_rejects_recorded_exclusions() -> None:
    tracks = [_track(path) for path in ("/a", "/b", "/c", "/excluded")]
    original = recommend_playlist(tracks, "harmonic_journey", DJControls(excluded_paths={"/excluded"}))
    result = recommendation_with_replacement(original, "/b", [tracks[-1]])
    assert {track.path for track in result.ordered_tracks} == {"/a", "/c"}


def test_recommendation_records_requested_genre() -> None:
    original = recommend_playlist([_track("/a")], "same_energy", DJControls(genre="House"))
    assert original.applied_controls["genre"] == "House"


@pytest.mark.parametrize("exclusion_source", ["original", "current", "removed"])
def test_desktop_backfill_rejects_exclusions(qapp, tmp_path, exclusion_source: str) -> None:
    tracks = [_track(path) for path in ("/a", "/b", "/c", "/excluded")]
    controls = DJControls(excluded_paths={"/excluded"} if exclusion_source == "original" else set())
    original = recommend_playlist(tracks[:3], "harmonic_journey", controls)
    window = MainWindow(scan_service=Mock(), repository=Mock(db_path=tmp_path / "library.db"))
    controller = window._library_controller
    controller._state = controller._state.model_copy(
        update={
            "scanned_records": tracks,
            "last_recommendation": original,
            "excluded_paths": frozenset({"/excluded"}) if exclusion_source == "current" else frozenset(),
            "playlist_removed_paths": frozenset({"/excluded"}) if exclusion_source == "removed" else frozenset(),
        }
    )
    result = controller._replacement_recommendation("/b")
    assert result is not None
    assert {track.path for track in result.ordered_tracks} == {"/a", "/c"}


def test_desktop_backfill_preserves_requested_genre(qapp, tmp_path) -> None:
    tracks = [_track("/a"), _track("/b"), _track("/wrong", genre="Rock")]
    original = recommend_playlist(tracks[:2], "harmonic_journey", DJControls(genre="House"))
    window = MainWindow(scan_service=Mock(), repository=Mock(db_path=tmp_path / "library.db"))
    controller = window._library_controller
    controller._state = controller._state.model_copy(
        update={"scanned_records": tracks, "last_recommendation": original}
    )
    result = controller._replacement_recommendation("/b")
    assert result is not None
    assert [track.path for track in result.ordered_tracks] == ["/a"]


@pytest.mark.parametrize("removed", ["/b", "/anchor"])
def test_desktop_backfill_keeps_explicit_anchor_and_locked_exception(qapp, tmp_path, removed: str) -> None:
    anchor, b, locked, wrong = (
        _track("/anchor"),
        _track("/b"),
        _track("/locked", energy=10),
        _track("/wrong", energy=10),
    )
    controls = DJControls(start_path=anchor.path, locked_paths={locked.path})
    original = recommend_playlist([anchor, b], "same_energy", DJControls(start_path=anchor.path))
    # A lock selected after generation is a legitimate strategy-filter exception.
    window = MainWindow(scan_service=Mock(), repository=Mock(db_path=tmp_path / "library.db"))
    controller = window._library_controller
    controller._state = controller._state.model_copy(
        update={
            "scanned_records": [wrong, anchor, b, locked],
            "last_recommendation": original,
            "locked_paths": frozenset(controls.locked_paths),
        }
    )
    result = controller._replacement_recommendation(removed)
    assert result is not None
    assert locked.path in {track.path for track in result.ordered_tracks}
    assert wrong.path not in {track.path for track in result.ordered_tracks}
    assert removed not in {track.path for track in result.ordered_tracks}


def test_desktop_backfill_preserves_manual_anchor_after_reordering(qapp, tmp_path) -> None:
    anchor, b, wrong, valid = _track("/anchor"), _track("/b"), _track("/wrong", energy=10), _track("/valid")
    original = recommend_playlist([anchor, b], "same_energy", DJControls(manual_order_paths=[anchor.path]))
    original = original.model_copy(update={"ordered_tracks": list(reversed(original.ordered_tracks))})
    window = MainWindow(scan_service=Mock(), repository=Mock(db_path=tmp_path / "library.db"))
    controller = window._library_controller
    controller._state = controller._state.model_copy(
        update={"scanned_records": [wrong, anchor, b, valid], "last_recommendation": original}
    )
    result = controller._replacement_recommendation("/b")
    assert result is not None
    assert [track.path for track in result.ordered_tracks] == ["/valid", "/anchor"]


def test_current_exclusion_overrides_original_locked_exception(qapp, tmp_path) -> None:
    anchor, b, locked = _track("/anchor"), _track("/b"), _track("/locked", energy=10)
    original = recommend_playlist([anchor, b, locked], "same_energy", DJControls(locked_paths={locked.path}))
    # Simulate a retained recommendation whose locked track was removed earlier.
    original = original.model_copy(update={"ordered_tracks": [anchor, b]})
    window = MainWindow(scan_service=Mock(), repository=Mock(db_path=tmp_path / "library.db"))
    controller = window._library_controller
    controller._state = controller._state.model_copy(
        update={
            "scanned_records": [anchor, b, locked],
            "last_recommendation": original,
            "excluded_paths": frozenset({locked.path}),
        }
    )
    result = controller._replacement_recommendation("/b")
    assert result is not None
    assert [track.path for track in result.ordered_tracks] == ["/anchor"]
