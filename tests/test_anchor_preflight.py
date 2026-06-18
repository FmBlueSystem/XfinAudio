from xfinaudio.library.models import MetadataStatus, TrackRecord
from xfinaudio.recommendation.candidate_pool import anchor_preflight_warnings
from xfinaudio.recommendation.controls import DJControls


def _track(path: str, title: str, status: MetadataStatus = "complete") -> TrackRecord:
    return TrackRecord(path=path, title=title, metadata_status=status)


def test_anchor_preflight_returns_no_warnings_without_controls() -> None:
    assert anchor_preflight_warnings(None, [_track("/ready.flac", "Ready")]) == []


def test_anchor_preflight_warns_when_start_or_end_track_is_unusable() -> None:
    controls = DJControls(start_path="/missing.flac", end_path="/incomplete.flac")
    records = [_track("/incomplete.flac", "Half Tagged", status="incomplete")]

    warnings = anchor_preflight_warnings(controls, records)

    assert warnings == [
        'Start track "missing.flac" is incomplete or unavailable and will be ignored.',
        'End track "Half Tagged" is incomplete or unavailable and will be ignored.',
    ]


def test_anchor_preflight_collapses_unusable_manual_tracks_into_count_warning() -> None:
    controls = DJControls(
        manual_order_paths=["/ready.flac", "/incomplete-manual.flac", "/missing.flac"],
    )
    records = [
        _track("/ready.flac", "Ready"),
        _track("/incomplete-manual.flac", "Incomplete Manual", status="incomplete"),
    ]

    warnings = anchor_preflight_warnings(controls, records)

    assert warnings == ["2 manually-ordered track(s) are incomplete or unavailable and will be ignored."]
