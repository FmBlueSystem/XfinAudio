import pytest

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


def test_half_time_pair_does_not_receive_unplayable_transition_penalty() -> None:
    score = optimizer._pair_score(
        track("/left.flac", bpm=84.6),
        track("/right.flac", bpm=169.0),
        None,
        optimizer.DEFAULT_WEIGHTS,
        optimizer.DEFAULT_SCORING_CONFIG,
        {},
        3.0,
    )

    assert score >= 0.0


def _hard_arc(pool: list[TrackRecord], **kwargs):
    return recommend_sequence(
        pool,
        arc_strategy="warmup",
        max_bpm_difference_percent=3.0,
        arc_length=kwargs.pop("arc_length", 4),
        **kwargs,
    )


def test_energy_arc_does_not_collapse_on_a_fragmented_shortlist() -> None:
    pool = [
        track("/anchor.flac", bpm=100.0, energy=2),
        track("/wrong-low.flac", bpm=140.0, energy=2),
        track("/bridge-1.flac", bpm=101.0, energy=4),
        track("/wrong-high.flac", bpm=160.0, energy=9),
        track("/bridge-2.flac", bpm=102.0, energy=7),
        track("/finish.flac", bpm=103.0, energy=9),
    ]

    result = _hard_arc(pool, start_path="/anchor.flac")

    assert len(result.ordered_tracks) == 4
    assert [item.path for item in result.ordered_tracks] == [
        "/anchor.flac",
        "/bridge-1.flac",
        "/bridge-2.flac",
        "/finish.flac",
    ]


def test_hard_arc_every_returned_edge_respects_the_bpm_ceiling() -> None:
    pool = [track(f"/t{i}.flac", bpm=bpm, energy=2 + i) for i, bpm in enumerate([100, 101, 102, 103, 140])]

    result = _hard_arc(pool, start_path="/t0.flac")

    assert all(
        optimizer.bpm_difference_percent(left.bpm or 0.0, right.bpm or 0.0) <= 3.0
        for left, right in zip(result.ordered_tracks, result.ordered_tracks[1:], strict=False)
    )


def test_hard_arc_reserves_a_reachable_end_for_the_terminal_slot() -> None:
    pool = _tempo_pool([100.0, 101.0, 102.0, 103.0, 104.0])

    result = _hard_arc(pool, start_path="/t0.flac", end_path="/t4.flac")

    assert result.ordered_tracks[-1].path == "/t4.flac"
    assert not result.warnings


def test_hard_arc_reports_a_proven_unreachable_end() -> None:
    pool = _tempo_pool([100.0, 101.0, 102.0, 160.0])

    result = _hard_arc(pool, start_path="/t0.flac", end_path="/t3.flac")

    assert not result.ordered_tracks
    assert any("proven infeasible" in warning.lower() for warning in result.warnings)


def test_hard_arc_distinguishes_budget_exhaustion_from_proven_infeasibility() -> None:
    pool = [track(f"/t{i}.flac", bpm=100.0 + i * 0.5, energy=(i % 9) + 1) for i in range(20)]

    exhausted = _hard_arc(pool, beam_width=0)
    infeasible = _hard_arc(_tempo_pool([100.0, 101.0]), arc_length=4, start_path="/t0.flac")

    assert any("budget" in warning.lower() and "not proof" in warning.lower() for warning in exhausted.warnings)
    assert any("proven infeasible" in warning.lower() for warning in infeasible.warnings)


def test_hard_arc_keeps_locked_paths_and_uses_manual_seam_as_external_root() -> None:
    seam = track("/manual.flac", bpm=99.0, energy=2)
    pool = [track(f"/t{i}.flac", bpm=100.0 + i, energy=3 + i) for i in range(5)]

    result = _hard_arc(
        pool,
        arc_length=5,
        target_length=4,
        external_start=seam,
        arc_slot_offset=1,
        mandatory_paths={"/t3.flac"},
    )

    assert len(result.ordered_tracks) == 4
    assert "/t3.flac" in {item.path for item in result.ordered_tracks}
    assert optimizer.bpm_difference_percent(seam.bpm or 0.0, result.ordered_tracks[0].bpm or 0.0) <= 3.0


def test_hard_arc_fails_closed_when_mandatory_paths_exceed_target() -> None:
    result = _hard_arc(
        _tempo_pool([100.0, 101.0, 102.0]),
        arc_length=2,
        target_length=2,
        mandatory_paths={"/t0.flac", "/t1.flac", "/t2.flac"},
    )

    assert not result.ordered_tracks
    assert any("mandatory" in warning.lower() and "proven infeasible" in warning.lower() for warning in result.warnings)


def test_hard_arc_fails_closed_when_mandatory_paths_cannot_coexist() -> None:
    result = _hard_arc(
        _tempo_pool([100.0, 101.0, 160.0]),
        arc_length=3,
        mandatory_paths={"/t1.flac", "/t2.flac"},
        start_path="/t0.flac",
    )

    assert not result.ordered_tracks
    assert any("mandatory" in warning.lower() for warning in result.warnings)


def test_hard_arc_defines_none_start_missing_bpm_and_uncapped_fallback() -> None:
    missing = track("/missing.flac", bpm=120.0).model_copy(update={"bpm": None})
    result = _hard_arc([missing, *_tempo_pool([100.0, 101.0, 102.0])])
    uncapped = recommend_sequence(
        _tempo_pool([100.0, 101.0, 102.0]),
        arc_strategy="warmup",
        max_bpm_difference_percent=3.0,
        arc_length=None,
    )

    assert len(result.ordered_tracks) == 4
    assert missing in result.ordered_tracks
    assert uncapped.optimizer in {"exact", "greedy-2opt"}


def test_hard_arc_one_track_can_be_both_start_and_end() -> None:
    only = track("/only.flac")

    result = _hard_arc([only], arc_length=1, start_path=only.path, end_path=only.path)

    assert result.ordered_tracks == [only]


def test_hard_arc_reports_a_mandatory_path_missing_from_the_pool() -> None:
    result = _hard_arc(_tempo_pool([100.0, 101.0, 102.0]), mandatory_paths={"/not-in-pool.flac"})

    assert not result.ordered_tracks
    assert any("not in the candidate pool" in warning.lower() for warning in result.warnings)


def test_hard_arc_neighbor_discovery_includes_folded_two_to_one_edges() -> None:
    pool = _tempo_pool([60.0, 120.0])

    result = _hard_arc(pool, arc_length=2, start_path="/t0.flac", end_path="/t1.flac")

    assert [item.path for item in result.ordered_tracks] == ["/t0.flac", "/t1.flac"]


def test_hard_arc_exact_and_beam_paths_are_deterministic_and_observable() -> None:
    small = _tempo_pool([100.0, 101.0, 102.0, 103.0])
    large = [track(f"/b{i:02d}.flac", bpm=100.0 + i * 0.1, energy=2 + i % 8) for i in range(20)]

    exact = _hard_arc(list(reversed(small)), start_path="/t0.flac")
    beam_first = _hard_arc(list(reversed(large)))
    beam_second = _hard_arc(large)

    assert exact.optimizer == "arc-subset-exact"
    assert beam_first.optimizer == "arc-subset-beam"
    assert [item.path for item in beam_first.ordered_tracks] == [item.path for item in beam_second.ordered_tracks]


def test_hard_arc_large_pool_never_builds_eager_score_or_arc_matrices(monkeypatch) -> None:
    pool = [track(f"/t{i:04d}.flac", bpm=120.0 + i % 10 * 0.1, energy=2 + i % 8) for i in range(2000)]
    monkeypatch.setattr(optimizer, "_score_matrix", lambda *args, **kwargs: pytest.fail("eager score matrix"))
    monkeypatch.setattr(optimizer, "_arc_bonuses", lambda *args, **kwargs: pytest.fail("eager arc matrix"))

    result = _hard_arc(pool)

    assert len(result.ordered_tracks) == 4


def test_hard_arc_exploration_only_caches_the_final_path_edges() -> None:
    pool = [track(f"/t{i:03d}.flac", bpm=120.0 + i % 12 * 0.1, energy=2 + i % 8) for i in range(200)]
    caller_cache = {}

    result = recommend_sequence(
        pool,
        start_path="/t000.flac",
        arc_strategy="warmup",
        max_bpm_difference_percent=3.0,
        arc_length=6,
        cache=caller_cache,
    )

    assert len(result.ordered_tracks) == 6
    assert len(caller_cache) == 5, "exploration must not retain full TransitionScore objects"


def test_hard_arc_beam_bounds_expensive_transition_scoring(monkeypatch) -> None:
    pool = [track(f"/t{i:04d}.flac", bpm=120.0 + i % 20 * 0.1, energy=2 + i % 8) for i in range(2000)]
    original = optimizer.score_transition
    calls = 0

    def counted_score_transition(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(optimizer, "score_transition", counted_score_transition)

    result = _hard_arc(pool, arc_length=6, start_path="/t0000.flac")

    assert len(result.ordered_tracks) == 6
    assert calls < 50_000, "beam exploration must preselect a bounded feasible successor budget"


def test_small_arc_domain_does_not_hide_a_low_arc_bonus_connector(monkeypatch) -> None:
    start = track("/start.flac", bpm=120.0, energy=10)
    connector = track("/zz-connector.flac", bpm=121.0, energy=1)
    decoys = [track(f"/decoy-{index:02d}.flac", bpm=121.0, energy=10) for index in range(70)]

    def connector_transition(left, right, **kwargs):
        return optimizer.TransitionScore(
            left_path=left.path,
            right_path=right.path,
            total_score=100.0 if right.path == connector.path else 0.0,
            component_scores={},
            explanations=[],
            warnings=[],
        )

    monkeypatch.setattr(optimizer, "score_transition", connector_transition)

    result = recommend_sequence(
        [start, connector, *decoys],
        start_path=start.path,
        arc_strategy="peak_time",
        max_bpm_difference_percent=3.0,
        arc_length=4,
    )

    assert connector.path in {item.path for item in result.ordered_tracks}


def test_beam_keeps_optional_successors_when_a_locked_track_is_not_a_neighbour() -> None:
    """A locked track that is not BPM-adjacent must not drain the frontier's neighbours.

    ``domain_neighbors`` is a generator. Testing ``candidate not in
    neighbor_candidates`` against the unplaced locked track consumes that
    one-shot iterator, so the optional successors the state needs to keep
    advancing silently vanish and a buildable arc is reported as
    unfinishable. This pool is a real interval graph driven through the real
    ``domain_neighbors``: ``/00-start`` (100 BPM) cannot jump straight to
    ``/50-locked`` (104 BPM, 4%), but both touch the bridge cluster at 102 BPM,
    so a four-track arc exists. Nothing here is monkeypatched.
    """
    start = track("/00-start.flac", bpm=100.0)
    locked = track("/50-locked.flac", bpm=104.0)
    bridges = [track(f"/10-fill-{index:02d}.flac", bpm=100.4 + index * 0.4) for index in range(16)]
    pool = sorted([start, locked, *bridges], key=lambda item: item.path)

    result = recommend_sequence(
        pool,
        start_path=start.path,
        arc_strategy="warmup",
        max_bpm_difference_percent=3.0,
        arc_length=4,
        mandatory_paths={locked.path},
    )

    assert result.optimizer == "arc-subset-beam"
    assert result.ordered_tracks, f"beam dropped a buildable arc: {result.warnings}"
    assert result.ordered_tracks[0].path == start.path
    assert locked.path in {item.path for item in result.ordered_tracks}
    assert len(result.ordered_tracks) == 4
    assert all(
        optimizer.bpm_difference_percent(left.bpm or 0.0, right.bpm or 0.0) <= 3.0
        for left, right in zip(result.ordered_tracks, result.ordered_tracks[1:], strict=False)
    )


def test_beam_retry_widens_a_pruned_bridge_into_the_path(monkeypatch) -> None:
    """A capped beam can prune the one bridge that finishes a small domain.

    The retry widens the beam and tries again, but no BPM pool can shape the
    failure the retry guards: it needs a bridge ranked below ``beam_width``
    high-scoring candidates that are all dead ends, and a BPM interval graph
    cannot hold 64 mutually non-adjacent dead ends beside the same terminal.
    So the neighbour graph is fabricated while the real
    ``_beam_arc_subset_path`` still runs, and a spy records the widths it is
    asked to run.
    """
    start = track("/01-start.flac", energy=5)
    leaves = [track(f"/02-leaf-{index:02d}.flac", energy=5) for index in range(65)]
    bridge = track("/03-bridge.flac", energy=5)
    bridge2 = track("/04-bridge2.flac", energy=5)
    end = track("/05-end.flac", energy=5)
    pool = [start, *leaves, bridge, bridge2, end]
    position = {item.path: index for index, item in enumerate(pool)}

    adjacency: dict[str, set[str]] = {item.path: set() for item in pool}

    def connect(left: TrackRecord, right: TrackRecord) -> None:
        adjacency[left.path].add(right.path)
        adjacency[right.path].add(left.path)

    for leaf in leaves:
        connect(start, leaf)
        connect(leaf, end)
    connect(start, bridge)
    connect(bridge, bridge2)
    connect(bridge2, end)

    def neighbors(index: int) -> tuple[int, ...]:
        return tuple(position[name] for name in sorted(adjacency[pool[index].path]))

    def expand_frontier(frontier: set[int]) -> set[int]:
        return {position[name] for index in frontier for name in adjacency[pool[index].path]}

    monkeypatch.setattr(
        optimizer, "_lazy_bpm_neighbors", lambda tracks, ceiling: (neighbors, frozenset(), expand_frontier)
    )

    leaf_paths = {leaf.path for leaf in leaves}

    def ranked_transition(left, right, **kwargs):
        total = 100.0 if left is not None and left.path == start.path and right.path in leaf_paths else 0.0
        return optimizer.TransitionScore(
            left_path="" if left is None else left.path,
            right_path=right.path,
            total_score=total,
            component_scores={},
            explanations=[],
            warnings=[],
        )

    monkeypatch.setattr(optimizer, "score_transition", ranked_transition)

    widths: list[int] = []
    original_beam = optimizer._beam_arc_subset_path

    def spy_beam(*args, **kwargs):
        widths.append(args[9])
        return original_beam(*args, **kwargs)

    monkeypatch.setattr(optimizer, "_beam_arc_subset_path", spy_beam)

    result = recommend_sequence(
        pool,
        start_path=start.path,
        end_path=end.path,
        arc_strategy="warmup",
        max_bpm_difference_percent=3.0,
        arc_length=4,
    )

    # The capped pass prunes the low-ranked bridge behind 64 dead-end leaves;
    # only the widened retry carries it and finishes the path.
    assert widths == [64, optimizer._beam_retry_width(64, len(pool))]
    assert widths[1] > widths[0]
    assert [item.path for item in result.ordered_tracks] == [start.path, bridge.path, bridge2.path, end.path]


def test_non_hard_arc_call_shapes_keep_the_legacy_solvers() -> None:
    pool = _tempo_pool([100.0, 101.0, 102.0, 103.0])

    no_arc = recommend_sequence(pool, max_bpm_difference_percent=3.0)
    no_ceiling = recommend_sequence(pool, arc_strategy="warmup", arc_length=3)

    assert no_arc.optimizer == "exact"
    assert len(no_arc.ordered_tracks) == 4
    assert no_ceiling.optimizer == "exact"
    assert len(no_ceiling.ordered_tracks) == 4


# ---------------------------------------------------------------------------
# Coverage hotspots: branches the existing arc/optimizer suites never reached.
#
# Each test below targets a behaviourally meaningful uncovered branch. Guard
# branches carry a one-line falsification note describing the mutation the
# assertion would catch. Ranges the public API cannot reach naturally are
# exercised through the private helper directly, as noted.
# ---------------------------------------------------------------------------


def test_arc_bonuses_treat_a_missing_energy_level_as_neutral() -> None:
    # Value: a pool containing an unanalyzed track (energy_level None) must still
    # produce a full arc-ordered set, not crash or drop the track. Catches a
    # regression where `_arc_bonuses` indexes energy_level without a None guard.
    pool = [track("/a.flac", "8A", 120.0, 2), track("/b.flac", "8A", 121.0, 5), track("/c.flac", "8A", 122.0, 8)]
    pool[1] = pool[1].model_copy(update={"energy_level": None})

    result = recommend_sequence(pool, arc_strategy="warmup")

    assert len(result.ordered_tracks) == 3
    assert result.optimizer == "exact"


def test_arc_subset_rejects_identical_start_and_end_for_a_multi_track_target() -> None:
    # Value: one path cannot be both the opener and the closer of a multi-track
    # set; the arc subset must warn instead of looping forever. Catches removal of
    # the start==end guard, which would otherwise try to place one index twice.
    pool = _tempo_pool([100.0, 101.0, 102.0])

    result = _hard_arc(pool, arc_length=3, start_path="/t0.flac", end_path="/t0.flac")

    assert not result.ordered_tracks
    assert any("both start and terminal" in warning for warning in result.warnings)


def test_arc_subset_reports_an_unplayable_external_start_seam() -> None:
    # Value: a manual seam the rest of the pool cannot follow from must be
    # reported as infeasible, not silently reordered. Catches removal of the
    # empty-initial-seam guard, which would let the subset start anywhere.
    seam = track("/seam.flac", bpm=100.0, energy=4)
    pool = _tempo_pool([160.0, 161.0, 162.0, 163.0])

    result = recommend_sequence(
        pool,
        external_start=seam,
        arc_strategy="warmup",
        max_bpm_difference_percent=3.0,
        arc_length=4,
    )

    assert not result.ordered_tracks
    assert any("BPM-compatible with the required start seam" in warning for warning in result.warnings)


def _install_neighbor_graph(
    monkeypatch: pytest.MonkeyPatch,
    pool: list[TrackRecord],
    edges: dict[int, tuple[int, ...]],
) -> None:
    def neighbors(index: int) -> tuple[int, ...]:
        return edges.get(index, ())

    def expand_frontier(frontier: set[int]) -> set[int]:
        return {candidate for index in frontier for candidate in edges.get(index, ())}

    monkeypatch.setattr(
        optimizer,
        "_lazy_bpm_neighbors",
        lambda *_args, **_kwargs: (neighbors, frozenset(), expand_frontier),
    )


def test_arc_subset_rejects_mandatory_paths_outside_the_fixed_end_hop_budget(monkeypatch) -> None:
    # Value: a locked path that is reachable but cannot fit before the required
    # end must fail closed, not be silently dropped from the set. Catches removal
    # of the mandatory-vs-search-domain check.
    pool = [track(f"/k{index}.flac") for index in range(3)]
    _install_neighbor_graph(monkeypatch, pool, {0: (1, 2), 1: (0,), 2: (0,)})

    result = recommend_sequence(
        pool,
        start_path="/k0.flac",
        end_path="/k2.flac",
        arc_strategy="warmup",
        max_bpm_difference_percent=3.0,
        arc_length=3,
        mandatory_paths={"/k1.flac"},
    )

    assert not result.ordered_tracks
    assert any("fixed-end hop budget" in warning for warning in result.warnings)


def test_arc_subset_rejects_a_fixed_end_domain_smaller_than_the_target(monkeypatch) -> None:
    # Value: too few candidates fit the fixed-end hop budget for the requested
    # length; the subset must say so rather than build a short set. Catches
    # removal of the search-domain size check.
    pool = [track(f"/m{index}.flac") for index in range(3)]
    _install_neighbor_graph(monkeypatch, pool, {0: (1, 2), 1: (0,), 2: (0,)})

    result = recommend_sequence(
        pool,
        start_path="/m0.flac",
        end_path="/m1.flac",
        arc_strategy="warmup",
        max_bpm_difference_percent=3.0,
        arc_length=3,
    )

    assert not result.ordered_tracks
    assert any("fixed-end hop budget" in warning for warning in result.warnings)


def test_arc_subset_reports_infeasibility_when_mandatory_paths_cannot_coexist(monkeypatch) -> None:
    # Value: two individually reachable locked tracks that cannot share one path
    # must be reported, not silently narrowed. Catches a regression where the
    # exact solver returns None but the caller treats it as an exhausted beam
    # (the wrong warning) or as success.
    #
    # Start (g0) and end (g3) are mandatory too, so the set is g0 + g1, g2, g3.
    # Both g1 and g2 touch only g0 and g3, so a four-slot path through both would
    # need a g1<->g2 edge that does not exist: no valid path exists even though
    # each mandatory path individually fits the hop budget.
    pool = [track(f"/g{index}.flac", energy=2 + index * 2) for index in range(5)]
    _install_neighbor_graph(
        monkeypatch,
        pool,
        {0: (1, 2, 4), 1: (0, 3), 2: (0, 3), 3: (1, 2, 4), 4: (0, 3)},
    )

    result = recommend_sequence(
        pool,
        start_path="/g0.flac",
        end_path="/g3.flac",
        arc_strategy="warmup",
        max_bpm_difference_percent=3.0,
        arc_length=4,
        mandatory_paths={"/g1.flac", "/g2.flac"},
    )

    assert not result.ordered_tracks
    assert any("satisfies every mandatory control" in warning for warning in result.warnings)


def test_arc_subset_treats_an_unknown_bpm_start_as_adjoining_every_track() -> None:
    # Value: a track without a usable BPM is a universal neighbour, so an
    # unknown-BPM anchor can still open an arc. Catches removal of the universal
    # fast-path, which would strand the anchor with no successors.
    pool = [
        track("/u0.flac", energy=2).model_copy(update={"bpm": None}),
        track("/u1.flac", bpm=120.0, energy=5),
        track("/u2.flac", bpm=121.0, energy=8),
    ]

    result = recommend_sequence(
        pool,
        start_path="/u0.flac",
        arc_strategy="warmup",
        max_bpm_difference_percent=3.0,
        arc_length=3,
    )

    assert len(result.ordered_tracks) == 3
    assert result.ordered_tracks[0].path == "/u0.flac"
    assert result.optimizer.startswith("arc-subset")


def test_arc_frontier_reaches_an_unknown_bpm_track_from_a_measurable_frontier() -> None:
    # Value: hop expansion must admit a track with no BPM even when the frontier
    # itself is all measurable. Catches removal of the unknown set from the
    # possible-frontier superset.
    pool = [track("/v0.flac", bpm=120.0, energy=2), track("/v1.flac", energy=5).model_copy(update={"bpm": None})]

    result = recommend_sequence(
        pool,
        start_path="/v0.flac",
        arc_strategy="warmup",
        max_bpm_difference_percent=3.0,
        arc_length=2,
    )

    assert len(result.ordered_tracks) == 2
    assert {item.path for item in result.ordered_tracks} == {"/v0.flac", "/v1.flac"}


def test_arc_frontier_rejects_a_candidate_only_inside_the_window_superset() -> None:
    # Value: the merged BPM windows are a fast superset; a candidate sitting
    # exactly on the window edge is 3.09% away and must still be rejected by the
    # real folded comparator. Catches removal of the superset validation, which
    # would admit unplayable neighbours.
    margin = 3.0 / 97.0
    pool = [track("/w0.flac", bpm=100.0, energy=2), track("/w1.flac", bpm=100.0 * (1.0 + margin), energy=5)]

    result = recommend_sequence(
        pool,
        start_path="/w0.flac",
        arc_strategy="warmup",
        max_bpm_difference_percent=3.0,
        arc_length=2,
    )

    assert not result.ordered_tracks
    assert any("BPM-reachable candidates" in warning for warning in result.warnings)


def test_expand_frontier_short_circuits_when_the_frontier_holds_an_unknown_bpm() -> None:
    # _reachable_indices returns early on this same condition, so the public arc
    # path cannot reach this guard; exercised directly. Falsification: dropping
    # the guard returns only the unknown index plus window matches, not the whole
    # universe, so the assertion fails.
    pool = [track("/x0.flac", bpm=120.0), track("/x1.flac").model_copy(update={"bpm": None})]

    _neighbors, unknown, expand_frontier = optimizer._lazy_bpm_neighbors(pool, 3.0)

    assert unknown == frozenset({1})
    assert expand_frontier({1}) == set(range(len(pool)))


def test_hop_distances_without_an_end_index_is_empty() -> None:
    # Falsification: without the None guard the walk calls neighbors(None); the
    # fake raises, so the assertion fails.
    def neighbors(_index: int):  # pragma: no cover - must never be called
        raise AssertionError("hop distances walked neighbours without an end index")

    assert optimizer._hop_distances(None, neighbors) == {}


def test_arc_subset_scores_a_locked_track_without_energy_as_neutral() -> None:
    # Value: a locked track the analyzer never assigned an energy level must stay
    # in the set without distorting the arc. Catches removal of the None-level
    # branch in the lazy arc bonus, which would raise on subtraction.
    pool = [
        track("/p0.flac", "8A", 100.0, 2),
        track("/p1.flac", "8A", 101.0, 3),
        track("/p2.flac", "8A", 102.0, 6),
        track("/locked.flac", "8A", 103.0, 8),
    ]
    pool[3] = pool[3].model_copy(update={"energy_level": None})

    result = recommend_sequence(
        pool,
        arc_strategy="warmup",
        max_bpm_difference_percent=3.0,
        arc_length=4,
        mandatory_paths={"/locked.flac"},
    )

    assert "/locked.flac" in {item.path for item in result.ordered_tracks}
    assert len(result.ordered_tracks) == 4


def test_recommend_sequence_rejects_an_unknown_start_path() -> None:
    pool = _tempo_pool([100.0, 101.0])

    with pytest.raises(ValueError, match="Unknown start_path"):
        recommend_sequence(pool, start_path="/missing.flac")


def test_recommend_sequence_rejects_an_unknown_end_path() -> None:
    pool = _tempo_pool([100.0, 101.0])

    with pytest.raises(ValueError, match="Unknown end_path"):
        recommend_sequence(pool, end_path="/missing.flac")


def test_recommend_sequence_rejects_a_start_equal_to_the_end_for_multiple_tracks() -> None:
    pool = _tempo_pool([100.0, 101.0])

    with pytest.raises(ValueError, match="must differ"):
        recommend_sequence(pool, start_path="/t0.flac", end_path="/t0.flac")


def test_heuristic_path_pins_a_terminal_end_for_a_large_pool() -> None:
    # Value: the greedy heuristic must reserve the required end for the final
    # slot even when the pool is too large for the exact solver. Catches removal
    # of the remove-end-from-remaining / append-end scaffolding.
    pool = [track(f"/h{index:02d}.flac", bpm=120.0 + index * 0.1, energy=2 + index % 8) for index in range(20)]

    result = recommend_sequence(pool, end_path="/h19.flac")

    assert result.optimizer == "greedy-2opt"
    assert len(result.ordered_tracks) == 20
    assert result.ordered_tracks[-1].path == "/h19.flac"


def test_beam_reserves_the_end_path_and_skips_it_before_the_terminal_slot() -> None:
    # Value: in the beam, a required end must not be placed before the last slot.
    # Catches removal of the mid-slot end_index filter, which would pin the end
    # early and leave the final slot open.
    pool = [track(f"/z{index:02d}.flac", bpm=120.0, energy=2 + index % 8) for index in range(20)]

    result = recommend_sequence(
        pool,
        end_path="/z19.flac",
        arc_strategy="warmup",
        max_bpm_difference_percent=3.0,
        arc_length=6,
    )

    assert result.optimizer == "arc-subset-beam"
    assert len(result.ordered_tracks) == 6
    assert result.ordered_tracks[-1].path == "/z19.flac"


def test_beam_rejects_a_mandatory_successor_that_cannot_finish() -> None:
    # No real BPM pool produces this: the pre-checks already guarantee each
    # mandatory path fits the hop budget, so the mandatory-successor rejection in
    # the beam is exercised directly. Falsification: dropping the
    # `_state_can_finish` guard would keep the dead-end successor and return a
    # path instead of (None, True).
    pool = [track(f"/b{index}.flac") for index in range(4)]

    path, exhausted = optimizer._beam_arc_subset_path(
        pool,
        target=2,
        initial=(0,),
        end_index=3,
        mandatory_mask=1 << 2,
        neighbors=lambda index: {0: (2, 3), 2: (3,)}.get(index, ()),
        hops_to_end={3: 0, 0: 1},
        transition=lambda _left, _right: 1.0,
        arc_bonus=lambda _index, _slot: 0.0,
        beam_width=4,
        candidate_domain_size=4,
    )

    assert path is None
    assert exhausted is True


def test_beam_skips_the_end_path_before_the_terminal_slot() -> None:
    # `_arc_subset_recommendation` folds the end into the mandatory mask, so the
    # mandatory check shadows this end-specific skip on the public path; the
    # beam is exercised directly. Falsification: removing the mid-slot end guard
    # would let the terminal track be selected early and the path is no longer
    # forced to reserve the final slot for it.
    pool = [track(f"/e{index}.flac") for index in range(4)]

    path, exhausted = optimizer._beam_arc_subset_path(
        pool,
        target=3,
        initial=(0,),
        end_index=3,
        mandatory_mask=0,
        neighbors=lambda index: {0: (1, 3), 1: (2,)}.get(index, ()),
        hops_to_end={3: 0, 0: 1, 1: 1},
        transition=lambda _left, _right: 1.0,
        arc_bonus=lambda _index, _slot: 0.0,
        beam_width=4,
        candidate_domain_size=4,
    )

    assert path is None
    assert exhausted is True


def test_beam_reports_no_valid_path_when_the_terminal_slot_cannot_be_satisfied() -> None:
    # A single-slot target skips the expansion loop entirely, leaving the
    # terminal-validity guard as the only place that can fail; exercised
    # directly. Falsification: removing the guard returns an empty path as a
    # success, so the assertion on `exhausted` fails.
    pool = [track("/b0.flac"), track("/b1.flac")]

    path, exhausted = optimizer._beam_arc_subset_path(
        pool,
        target=1,
        initial=(0,),
        end_index=1,
        mandatory_mask=0,
        neighbors=lambda _index: (),
        hops_to_end={},
        transition=lambda _left, _right: 1.0,
        arc_bonus=lambda _index, _slot: 0.0,
        beam_width=1,
        candidate_domain_size=2,
    )

    assert path is None
    assert exhausted is True
