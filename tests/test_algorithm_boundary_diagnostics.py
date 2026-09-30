"""Numerical boundaries and late-cap diagnostics remain honest."""

import pytest

from xfinaudio.audio.spectral_profile import SpectralProfile
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import recommend_playlist
from xfinaudio.recommendation.prep_copilot import DJSetIntent, build_prep_copilot_plan


def record(path: str) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=path,
        bpm=120,
        camelot_key="8A",
        energy_level=5,
        duration=240,
        genre="House",
        metadata_status="complete",
    )


@pytest.mark.parametrize("strategy", ["same_color", "same_color_energy"])
@pytest.mark.parametrize("green,eligible", [(0.04, True), (0.040001, False)])
def test_color_inclusive_mathematical_boundary(strategy: str, green: float, eligible: bool) -> None:
    anchor = record("a").model_copy(
        update={
            "spectral_profile": SpectralProfile(
                red_ratio=1, green_ratio=0, blue_ratio=0, centroid_hz=1000, rolloff_hz=2000, dominant_color="RED"
            )
        }
    )
    candidate = record("b").model_copy(
        update={
            "spectral_profile": SpectralProfile(
                red_ratio=1 - green,
                green_ratio=green,
                blue_ratio=0,
                centroid_hz=1000,
                rolloff_hz=2000,
                dominant_color="RED",
            )
        }
    )
    result = recommend_playlist([anchor, candidate], strategy, DJControls(start_path="a"), target_count=2)
    assert ("b" in [t.path for t in result.ordered_tracks]) is eligible


def test_prep_count_cap_explains_resulting_duration_shortfall() -> None:
    plan = build_prep_copilot_plan(
        [record(str(i)) for i in range(30)], DJSetIntent(name="cap", target_track_count=3, target_minutes=20)
    )
    for variant in plan.variants:
        assert len(variant.recommendation.ordered_tracks) == 3
        assert any("count cap" in text.lower() and "duration" in text.lower() for text in variant.warnings)
        assert variant.readiness.status == "needs_review"


def test_zero_match_genre_note_does_not_claim_every_track_matched() -> None:
    plan = build_prep_copilot_plan(
        [record(str(i)) for i in range(5)], DJSetIntent(name="genre", target_track_count=3, genre_focus="Jazz")
    )
    for variant in plan.variants[:2]:
        assert not any("matched all" in note for note in variant.pool_notes)
        assert any("no match" in note.lower() for note in variant.pool_notes)
