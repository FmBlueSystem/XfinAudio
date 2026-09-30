"""Bounded policy metadata captures the actual generation-time filter context."""

import pytest

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.loudness_policy import LoudnessBand
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation, recommend_playlist


@pytest.mark.parametrize(
    "strategy,genre,expected",
    [
        ("same_energy", " House ", "house"),
        ("same_energy", "absent", None),
        ("same_genre", None, "house"),
    ],
)
def test_recommendation_captures_resolved_policy(strategy, genre, expected) -> None:
    tracks = [
        TrackRecord(path=p, energy_level=5, bpm=120, genre="House", metadata_status="complete") for p in ("a", "b")
    ]
    original = recommend_playlist(
        tracks, strategy, DJControls(start_path="a", genre=genre), loudness_band=LoudnessBand(-18, 1)
    )
    policy = original.replacement_policy
    assert policy is not None
    assert policy.genre == expected
    assert policy.energy_anchor == 5
    assert policy.loudness_band == LoudnessBand(-18, 1)
    restored = PlaylistRecommendation.model_validate_json(original.model_dump_json())
    assert restored.replacement_policy == policy
    assert "raw_metadata" not in policy.model_dump_json()
