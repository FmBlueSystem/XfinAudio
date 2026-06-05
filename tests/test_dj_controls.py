import pytest
from pydantic import ValidationError

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls, apply_controls


def track(path: str) -> TrackRecord:
    return TrackRecord(path=path, metadata_status="complete")


def test_apply_controls_preserves_locked_tracks_in_candidates() -> None:
    tracks = [track("/a.flac"), track("/b.flac")]
    controls = DJControls(locked_paths={"/b.flac"})

    result = apply_controls(tracks, controls)

    assert [item.path for item in result.candidate_tracks] == ["/a.flac", "/b.flac"]
    assert result.locked_paths == ["/b.flac"]


def test_apply_controls_removes_excluded_tracks() -> None:
    tracks = [track("/a.flac"), track("/b.flac")]
    controls = DJControls(excluded_paths={"/a.flac"})

    result = apply_controls(tracks, controls)

    assert [item.path for item in result.candidate_tracks] == ["/b.flac"]
    assert result.excluded_paths == ["/a.flac"]


def test_apply_controls_validates_start_and_end_paths_exist() -> None:
    tracks = [track("/a.flac")]
    controls = DJControls(start_path="/missing.flac")

    with pytest.raises(ValueError, match="Unknown start_path"):
        apply_controls(tracks, controls)


def test_apply_controls_preserves_manual_order_first_and_in_order() -> None:
    tracks = [track("/a.flac"), track("/b.flac"), track("/c.flac")]
    controls = DJControls(manual_order_paths=["/c.flac", "/a.flac"])

    result = apply_controls(tracks, controls)

    assert [item.path for item in result.manual_prefix] == ["/c.flac", "/a.flac"]
    assert [item.path for item in result.candidate_tracks] == ["/c.flac", "/a.flac", "/b.flac"]


def test_controls_reject_excluded_locked_overlap() -> None:
    with pytest.raises(ValidationError, match="excluded paths cannot overlap locked paths"):
        DJControls(locked_paths={"/a.flac"}, excluded_paths={"/a.flac"})


def test_controls_reject_excluded_start_or_end_overlap() -> None:
    with pytest.raises(ValidationError, match="excluded paths cannot contain start_path"):
        DJControls(start_path="/a.flac", excluded_paths={"/a.flac"})

    with pytest.raises(ValidationError, match="excluded paths cannot contain end_path"):
        DJControls(end_path="/b.flac", excluded_paths={"/b.flac"})


def test_controls_reject_duplicate_manual_order_paths() -> None:
    with pytest.raises(ValidationError, match="manual order paths cannot contain duplicates"):
        DJControls(manual_order_paths=["/a.flac", "/a.flac"])
