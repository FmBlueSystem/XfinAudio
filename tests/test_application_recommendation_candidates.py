from __future__ import annotations

from pathlib import Path

from xfinaudio.audio.spectral_profile import ColorName, SpectralProfile
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls


def _record(path: str, *, genre: str | None = None, tags: list[str] | None = None) -> TrackRecord:
    return TrackRecord(path=path, metadata_status="complete", genre=genre, tags=tags or [])


def _spectral_record(path: str, color: ColorName) -> TrackRecord:
    return _record(path).model_copy(
        update={
            "spectral_profile": SpectralProfile(
                red_ratio=1.0 if color == "RED" else 0.0,
                green_ratio=1.0 if color == "GREEN" else 0.0,
                blue_ratio=1.0 if color == "BLUE" else 0.0,
                dominant_color=color,
            )
        }
    )


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


def test_application_candidate_pool_prefilters_by_strategy_before_the_interactive_cap() -> None:
    from xfinaudio.application.recommendation_candidates import plan_recommendation_candidates

    reds = [_spectral_record(f"/a-red-{index:02d}.mp3", "RED") for index in range(30)]
    greens = [_spectral_record(f"/b-green-{index:02d}.mp3", "GREEN") for index in range(30)]

    result = plan_recommendation_candidates(
        scanned_records=[*reds, *greens],
        controls=DJControls(start_path="/b-green-00.mp3"),
        limit=25,
        strategy_name="same_color",
    )

    assert len(result) == 25
    assert all(track.spectral_profile is not None for track in result)
    assert {track.spectral_profile.dominant_color for track in result} == {"GREEN"}


def test_application_candidate_pool_keeps_legacy_behavior_without_a_strategy() -> None:
    from xfinaudio.application.recommendation_candidates import plan_recommendation_candidates

    reds = [_spectral_record(f"/a-red-{index:02d}.mp3", "RED") for index in range(30)]
    greens = [_spectral_record(f"/b-green-{index:02d}.mp3", "GREEN") for index in range(30)]

    result = plan_recommendation_candidates(
        scanned_records=[*reds, *greens],
        controls=None,
        limit=25,
    )

    assert [track.path for track in result] == [red.path for red in reds[:25]]


def test_desktop_main_window_imports_application_candidate_boundary() -> None:
    source = Path("src/xfinaudio/desktop/main_window.py").read_text()

    assert "from xfinaudio.application.recommendation_candidates import plan_recommendation_candidates" in source
    assert "from xfinaudio.recommendation.candidate_pool import build_recommendation_pool" not in source
