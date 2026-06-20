from __future__ import annotations

from pathlib import Path

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls


def _record(path: str, *, genre: str | None = None, tags: list[str] | None = None) -> TrackRecord:
    return TrackRecord(path=path, metadata_status="complete", genre=genre, tags=tags or [])


def test_application_candidate_pool_preserves_control_priority() -> None:
    from xfinaudio.application.recommendation_candidates import plan_recommendation_candidates

    priority = _record("/priority.mp3")
    other = _record("/other.mp3")

    result = plan_recommendation_candidates(
        scanned_records=[other, priority],
        controls=DJControls(start_path="/priority.mp3"),
        limit=25,
    )

    assert [track.path for track in result] == ["/priority.mp3", "/other.mp3"]


def test_application_candidate_pool_preserves_compatible_ordering() -> None:
    from xfinaudio.application.recommendation_candidates import plan_recommendation_candidates

    anchor = _record("/anchor.mp3", genre="techno")
    compatible = _record("/compatible.mp3", genre="techno")
    unrelated = _record("/unrelated.mp3", genre="jazz")

    result = plan_recommendation_candidates(
        scanned_records=[anchor, unrelated, compatible],
        controls=DJControls(start_path="/anchor.mp3"),
        limit=25,
    )

    paths = [track.path for track in result]
    assert paths.index("/compatible.mp3") < paths.index("/unrelated.mp3")


def test_desktop_main_window_imports_application_candidate_boundary() -> None:
    source = Path("src/xfinaudio/desktop/main_window.py").read_text()

    assert "from xfinaudio.application.recommendation_candidates import plan_recommendation_candidates" in source
    assert "from xfinaudio.recommendation.candidate_pool import build_recommendation_pool" not in source
