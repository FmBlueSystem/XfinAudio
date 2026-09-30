"""Safe local Live ranking with synthetic metadata; no playback or network."""

from tests.test_ai_narrator_controller import _readiness, _recommendation, _track
from xfinaudio.desktop.live_assistance import live_session_ready, rank_live_candidates
from xfinaudio.recommendation.scoring import TransitionScoringConfig, score_transition


def _set():
    tracks = [_track("/a"), _track("/b").model_copy(update={"camelot_key": "9A"}), _track("/c")]
    return _recommendation([track.model_copy(update={"genre": "House"}) for track in tracks])


def test_live_readiness_fails_closed_for_absent_invalid_and_stale_data() -> None:
    recommendation = _set()
    assert live_session_ready(recommendation, _readiness())
    assert not live_session_ready(None, _readiness())
    assert not live_session_ready(recommendation, None)
    assert not live_session_ready(recommendation, _readiness().model_copy(update={"status": "blocked"}))
    assert not live_session_ready(recommendation, _readiness(), excluded_paths=frozenset({"/b"}))
    assert not live_session_ready(recommendation, _readiness(), locked_paths=frozenset({"/missing"}))
    broken = recommendation.model_copy(
        update={"ordered_tracks": [_track("/a"), _track("/b").model_copy(update={"bpm": None})]}
    )
    assert not live_session_ready(broken, _readiness())
    invalid_key = recommendation.model_copy(
        update={"ordered_tracks": [_track("/a"), _track("/b").model_copy(update={"camelot_key": "??"})]}
    )
    assert not live_session_ready(invalid_key, _readiness())


def test_live_ranking_uses_actual_engine_scores_not_pool_positions() -> None:
    recommendation = _set()
    ranked = rank_live_candidates(recommendation, ("/a",))
    assert [item.track.path for item in ranked] == ["/c", "/b"]
    expected = score_transition(
        recommendation.ordered_tracks[0],
        recommendation.ordered_tracks[2],
        config=TransitionScoringConfig(weights=recommendation.strategy.weights),
    )
    assert ranked[0].score == expected
    assert ranked[0].readiness.status == "ready"
    assert all(item.track.path != "/a" for item in ranked)
    assert rank_live_candidates(recommendation, ("/unknown",)) == []
    assert rank_live_candidates(recommendation, ("/a", "/a")) == []


def test_live_preserves_end_manual_controls_and_exclusions() -> None:
    recommendation = _set()
    end_bound = recommendation.model_copy(update={"applied_controls": {"end_path": "/c"}})
    assert [item.track.path for item in rank_live_candidates(end_bound, ("/a",))] == ["/b"]
    manual = recommendation.model_copy(update={"applied_controls": {"manual_order_paths": ["/a", "/b"]}})
    assert [item.track.path for item in rank_live_candidates(manual, ("/a",))] == ["/b"]
    assert rank_live_candidates(recommendation, ("/a",), excluded_paths=frozenset({"/b"})) == []
    assert rank_live_candidates(recommendation, ("/a", "/b", "/c")) == []


def test_live_never_offers_a_transition_or_remaining_order_needing_review() -> None:
    recommendation = _set()
    tracks = [*recommendation.ordered_tracks, _track("/unsafe").model_copy(update={"bpm": 170.0})]
    unsafe = recommendation.model_copy(update={"ordered_tracks": tracks})
    assert not live_session_ready(unsafe, _readiness())
    assert rank_live_candidates(unsafe, ("/a",)) == []
