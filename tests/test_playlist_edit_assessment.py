"""Conversational proposals must pass the real musical engine before applying."""

import pytest

from xfinaudio.application.playlist_edit_assessment import assess_playlist_edit
from xfinaudio.library.models import TrackRecord


def tracks():
    return [
        TrackRecord(path=p, bpm=120, camelot_key="8A", energy_level=e, metadata_status="complete")
        for p, e in (("a", 3), ("b", 8))
    ]


def test_assessment_scores_actual_adjacency_and_shows_engine_review_warnings():
    result = assess_playlist_edit(("b", "a"), tracks())
    assert result.recommendation.transition_scores[0].left_path == "b"
    assert result.recommendation.transition_scores[0].right_path == "a"
    assert result.quality.transition_count == 1
    assert result.readiness.status == "needs_review"
    assert "energía" in result.description


@pytest.mark.parametrize(
    "update",
    [
        {"bpm": float("nan")},
        {"camelot_key": "garbage"},
        {"energy_level": 11},
        {"bpm": None},
        {"metadata_status": "incomplete"},
    ],
)
def test_bad_metadata_and_hard_readiness_blockers_reject_proposals(update):
    records = tracks()
    records[0] = records[0].model_copy(update=update)
    with pytest.raises(ValueError):
        assess_playlist_edit(("a", "b"), records)


def test_unknown_tracks_or_too_small_set_are_blocked_without_fabrication():
    with pytest.raises(ValueError, match="metadata"):
        assess_playlist_edit(("a", "unknown"), tracks())
    with pytest.raises(ValueError, match="2 pistas"):
        assess_playlist_edit(("a",), tracks())


def test_assessment_cannot_score_excluded_paths_as_an_approved_order():
    with pytest.raises(ValueError, match="excluded"):
        assess_playlist_edit(("a", "b"), tracks(), excluded_paths={"b"})
