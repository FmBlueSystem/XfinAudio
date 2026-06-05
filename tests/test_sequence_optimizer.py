from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation import optimizer
from xfinaudio.recommendation.optimizer import recommend_sequence


def track(path: str, key: str = "8A", bpm: float = 120.0, energy: int = 5) -> TrackRecord:
    return TrackRecord(
        path=path,
        bpm=bpm,
        camelot_key=key,
        energy_level=energy,
        genre="House",
        tags=["Peak"],
        metadata_status="complete",
    )


def test_recommend_sequence_uses_exact_optimizer_for_small_track_sets() -> None:
    tracks = [
        track("/track-b.flac", "8A", 120.0, 5),
        track("/track-c.flac", "4A", 132.0, 9),
        track("/track-a.flac", "8A", 120.0, 5),
    ]

    result = recommend_sequence(tracks)

    assert [item.path for item in result.ordered_tracks] == ["/track-a.flac", "/track-b.flac", "/track-c.flac"]
    assert result.total_score == result.transition_scores[0].total_score + result.transition_scores[1].total_score


def test_recommend_sequence_respects_start_and_end_constraints() -> None:
    tracks = [
        track("/track-b.flac", "8A", 120.0, 5),
        track("/track-c.flac", "4A", 132.0, 9),
        track("/track-a.flac", "8A", 120.0, 5),
    ]

    result = recommend_sequence(tracks, start_path="/track-c.flac", end_path="/track-b.flac")

    assert [item.path for item in result.ordered_tracks] == ["/track-c.flac", "/track-a.flac", "/track-b.flac"]


def test_recommend_sequence_routes_twenty_tracks_to_exact_optimizer(monkeypatch) -> None:
    tracks = [track(f"/track-{index:02d}.flac") for index in range(20)]
    calls: list[int] = []

    def fake_exact_path(*args, **kwargs) -> tuple[int, ...]:
        calls.append(len(args[0]))
        return tuple(range(20))

    monkeypatch.setattr(optimizer, "_exact_path", fake_exact_path)

    result = recommend_sequence(tracks, exact_limit=20)

    assert calls == [20]
    assert result.optimizer == "exact"


def test_recommend_sequence_passes_controlled_boost_rules_to_transition_scores() -> None:
    tracks = [
        track("/track-a.flac", "8A", 120.0, 5),
        track("/track-b.flac", "10A", 120.0, 5),
    ]

    result = recommend_sequence(tracks, boost_rules={("8A", "10A")})

    assert result.transition_scores[0].component_scores["harmonic"] == 0.8


def test_recommend_sequence_uses_deterministic_greedy_two_opt_for_large_track_sets() -> None:
    tracks = [
        track(f"/track-{index:02d}.flac", key=f"{(index % 12) + 1}A", bpm=120.0 + index % 4, energy=4 + index % 3)
        for index in range(21)
    ]

    first = recommend_sequence(list(reversed(tracks)), exact_limit=20)
    second = recommend_sequence(tracks, exact_limit=20)

    assert [item.path for item in first.ordered_tracks] == [item.path for item in second.ordered_tracks]
    assert sorted(item.path for item in first.ordered_tracks) == sorted(item.path for item in tracks)
    assert len(first.transition_scores) == 20
