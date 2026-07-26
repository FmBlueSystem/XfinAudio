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


def test_recommend_sequence_uses_exact_solver_for_n_15(monkeypatch) -> None:
    """15 tracks is within the exact_limit boundary — exact solver runs."""
    tracks = [track(f"/track-{index:02d}.flac") for index in range(15)]
    called_exact = False

    original_exact = optimizer._exact_path

    def spy_exact(*args, **kwargs):
        nonlocal called_exact
        called_exact = True
        return original_exact(*args, **kwargs)

    monkeypatch.setattr(optimizer, "_exact_path", spy_exact)

    result = recommend_sequence(tracks)  # default exact_limit=15

    assert len(result.ordered_tracks) == 15
    assert result.optimizer == "exact"
    assert called_exact is True


def test_recommend_sequence_uses_heuristic_for_n_16() -> None:
    """16 tracks exceeds exact_limit — falls back to greedy-2opt heuristic."""
    tracks = [track(f"/track-{index:02d}.flac") for index in range(16)]

    result = recommend_sequence(tracks)  # default exact_limit=15

    assert len(result.ordered_tracks) == 16
    assert result.optimizer == "greedy-2opt"


def _energy_spread(recommendation) -> int:
    levels = [t.energy_level for t in recommendation.ordered_tracks if t.energy_level]
    return max(levels) - min(levels) if levels else 0


def test_journey_traces_an_arc_instead_of_holding_one_level() -> None:
    """Scoring only adjacent pairs makes a flat set optimal; a set needs a shape.

    Energy scores highest when two tracks match, so maximizing the sum of
    adjacent scores rewards never changing level. On a real library that
    produced sets spanning 2.2 of 10 levels, one of them 25 tracks all at 7.
    """
    tracks = [
        TrackRecord(
            path=f"/t{index}.flac",
            title=f"T{index}",
            bpm=126.0,
            camelot_key="8A",
            energy_level=1 + index % 10,
            duration=240.0,
            genre="House",
            tags=["house"],
            metadata_status="complete",
        )
        for index in range(30)
    ]

    recommendation = recommend_sequence(tracks, arc_strategy="harmonic_journey")
    levels = [t.energy_level for t in recommendation.ordered_tracks if t.energy_level is not None]

    assert _energy_spread(recommendation) >= 5, levels
    peak_index = levels.index(max(levels))
    assert peak_index >= len(levels) // 2, f"peak at {peak_index} of {len(levels)}: {levels}"


def test_arc_changes_the_order_when_a_shape_is_requested() -> None:
    """Without a strategy the solver keeps its original scoring path.

    Asking for a shape has to change the result, or the arc term is inert.
    """
    tracks = [
        TrackRecord(
            path=f"/t{index}.flac",
            title=f"T{index}",
            bpm=126.0,
            camelot_key="8A",
            energy_level=1 + index % 10,
            duration=240.0,
            genre="House",
            tags=["house"],
            metadata_status="complete",
        )
        for index in range(30)
    ]

    without_arc = recommend_sequence(tracks)
    with_arc = recommend_sequence(tracks, arc_strategy="harmonic_journey")

    flat_spread = _energy_spread(without_arc)
    shaped_spread = _energy_spread(with_arc)

    assert [t.path for t in without_arc.ordered_tracks] != [t.path for t in with_arc.ordered_tracks]
    assert shaped_spread >= flat_spread


# ---------------------------------------------------------------------------
# The curve has to span the set the DJ plays, not the pool it was drawn from.
#
# `_arc_bonuses` sized the shape by `len(tracks)` -- the whole candidate pool,
# around 120 -- and the result is then trimmed to the ~15 that fill the slot.
# The DJ saw the first 12% of the curve. Measured on the real library: rho
# +0.386 sizing by the pool against +0.806 sizing by the set.
# ---------------------------------------------------------------------------


def _energy_pool(levels: list[int]) -> list[TrackRecord]:
    return [
        TrackRecord(
            path=f"/e{index}.flac",
            title=f"e{index}",
            bpm=120.0 + index * 0.3,
            camelot_key="8A",
            energy_level=level,
            metadata_status="complete",
        )
        for index, level in enumerate(levels)
    ]


def test_arc_is_sized_by_the_set_not_the_pool() -> None:
    """A warm-up that only ever shows its first slots never gets to climb."""
    pool = _energy_pool([2, 3, 4, 5, 6, 7] * 6)

    played = recommend_sequence(pool, arc_strategy="warmup", arc_weight=1.4, arc_length=8).ordered_tracks[:8]

    levels = [item.energy_level for item in played if item.energy_level is not None]
    assert levels[-1] > levels[0], f"did not climb inside the played set: {levels}"


def test_arc_length_defaults_to_the_pool() -> None:
    """Callers that do not know their set length keep the old behaviour."""
    pool = _energy_pool([2, 4, 6, 3, 5, 7])

    assert recommend_sequence(pool, arc_strategy="warmup").ordered_tracks


def test_anchor_is_excluded_from_the_energy_scale() -> None:
    """The DJ's pick is regularly outside the strategy's own band.

    One anchor at level 9 over a pool spanning 2-5 stretched the scale to 2-9,
    so the curve's top asked for a level nothing in the pool could supply and
    every candidate scored equally far from it.
    """
    pool = _energy_pool([9, 2, 3, 4, 5, 2, 3, 4, 5])

    played = recommend_sequence(
        pool, start_path="/e0.flac", arc_strategy="warmup", arc_weight=1.4, arc_length=9
    ).ordered_tracks

    levels = [item.energy_level for item in played[1:] if item.energy_level is not None]
    assert levels[-1] > levels[0], f"anchor at 9 flattened the climb: {levels}"


# ---------------------------------------------------------------------------
# An unplayable tempo jump is not a bad option, it is not an option.
#
# The BPM difference was only ever a scoring component, so the sequencer would
# happily place a 138 next to a 120 if the harmony was good enough. Measured on
# the real library: 11 of 12 peak_time sets contained a jump above the declared
# 3% ceiling, the worst of them 47.89%. A DJ cannot beatmatch that -- a CDJ's
# pitch fader is +/-6% or +/-8%, and 6% already moves the key a full semitone.
# ---------------------------------------------------------------------------


def _tempo_pool(bpms: list[float]) -> list[TrackRecord]:
    return [
        TrackRecord(
            path=f"/t{index}.flac",
            title=f"t{index}",
            bpm=bpm,
            camelot_key="8A",
            energy_level=6,
            metadata_status="complete",
        )
        for index, bpm in enumerate(bpms)
    ]


def _worst_jump(tracks: list[TrackRecord]) -> float:
    bpms = [item.bpm for item in tracks if item.bpm is not None]
    return max((abs(b - a) / a * 100 for a, b in zip(bpms, bpms[1:], strict=False)), default=0.0)


def test_the_sequencer_does_not_build_an_unplayable_jump() -> None:
    """Two reachable clusters: the order has to walk between them, not leap."""
    pool = _tempo_pool([120.0, 121.0, 122.0, 123.0, 124.0, 125.0, 126.0, 127.0])

    ordered = recommend_sequence(pool, max_bpm_difference_percent=3.0).ordered_tracks

    assert len(ordered) == len(pool)
    assert _worst_jump(ordered) <= 3.0, f"worst jump {_worst_jump(ordered):.2f}%"


def test_a_stranded_track_is_parked_at_the_end_not_spliced_into_the_middle() -> None:
    """The sequencer orders everything it is handed; dropping is the caller's job.

    So the one unavoidable bad seam belongs at the edge, where the caller can
    cut it off without losing the playable chain in front of it.
    """
    pool = _tempo_pool([120.0, 121.0, 122.0, 190.0])

    ordered = recommend_sequence(pool, start_path="/t0.flac", max_bpm_difference_percent=3.0).ordered_tracks

    assert ordered[-1].path == "/t3.flac"
    assert _worst_jump(ordered[:-1]) <= 3.0


def test_the_ceiling_is_off_by_default() -> None:
    """Callers that never asked for the constraint keep their behaviour."""
    pool = _tempo_pool([120.0, 190.0])

    assert len(recommend_sequence(pool).ordered_tracks) == 2
