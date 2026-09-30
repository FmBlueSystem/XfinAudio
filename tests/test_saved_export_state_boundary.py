"""A saved set exports its exact contents with current, not previous-set readiness."""

import pytest

from tests.test_ai_shell_navigation import EmptyScanner
from tests.test_live_assistance import _set
from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.exporting.serato_crate import parse_serato_crate_bytes
from xfinaudio.exporting.serato_playlist_exporter import SeratoLibrary
from xfinaudio.library.track_repository import TrackRepository
from xfinaudio.quality.dj_readiness import build_dj_readiness_report
from xfinaudio.quality.recommendation_quality import build_quality_report


@pytest.mark.parametrize("missing_metadata", [False, True])
def test_saved_export_uses_current_order_and_readiness(qapp, tmp_path, monkeypatch, missing_metadata):
    serato = tmp_path / "_Serato_"
    (serato / "Subcrates").mkdir(parents=True)
    tracks = []
    for name, source in zip(("A", "B"), _set().ordered_tracks, strict=False):
        path = tmp_path / f"{name}.flac"
        path.write_bytes(b"synthetic fixture, never decoded")
        tracks.append(source.model_copy(update={"path": str(path), "title": name, "bpm": 120.0}))
    if missing_metadata:
        tracks[0] = tracks[0].model_copy(update={"bpm": None, "metadata_status": "incomplete"})
    monkeypatch.setattr(
        "xfinaudio.desktop.export_coordinator.discover_serato_libraries",
        lambda: [SeratoLibrary(serato_folder=serato, volume_root=tmp_path)],
    )
    window = MainWindow(scan_service=EmptyScanner(), repository=TrackRepository(tmp_path / "tracks.db"))
    try:
        old = _set()
        old_quality = build_quality_report(old)
        old_readiness = build_dj_readiness_report(old, old_quality).model_copy(
            update={"status": "ready" if missing_metadata else "blocked", "blocker_count": 0 if missing_metadata else 1}
        )
        state = window._state.with_scanned_records(tracks).model_copy(
            update={
                "last_recommendation": old,
                "last_quality_report": old_quality,
                "last_dj_readiness_report": old_readiness,
                "playlist_removed_paths": frozenset({tracks[0].path}),
                "excluded_paths": frozenset({tracks[0].path}),
                "locked_paths": frozenset({"/unrelated-locked"}),
                "applied_variant_name": "safe",
                "ai_narrative_text": "Old set commentary",
            }
        )
        window._replace_app_state(state)
        saved = window._playlist_repository.create("Saved exact set", [track.path for track in tracks])
        window._playlist_coordinator.export_playlist(saved.id)
        assert window._state.playlist_removed_paths == frozenset()
        assert window._state.last_quality_report.track_count == 2
        assert window._state.last_quality_report.transition_count == 1
        assert window._state.last_quality_report is not old_quality
        assert window._state.last_dj_readiness_report is not old_readiness
        assert window._state.applied_variant_name is None
        assert window._state.ai_narrative_text is None
        assert window._state.excluded_paths == state.excluded_paths
        assert window._state.locked_paths == state.locked_paths
        assert window._state.last_recommendation.applied_controls == {}
        target = serato / "Subcrates" / "Saved exact set.crate"
        if missing_metadata:
            assert not target.exists()
            assert window._state.last_dj_readiness_report.status == "blocked"
        else:
            assert target.exists(), window.status_label.text()
            assert parse_serato_crate_bytes(target.read_bytes()).paths == ("A.flac", "B.flac")
            assert window._state.last_dj_readiness_report.status != "blocked"
    finally:
        window.close()
