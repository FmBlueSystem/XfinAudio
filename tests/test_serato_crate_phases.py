"""Split an ordered set into its own energy phases: Apertura, Subida, Pico, Cierre (S4, S5).

The phases come from the tracks' own Mixed In Key energies, never from the strategy: the
list is normalised to its own range, gaps take the nearest known energy, an edge-clamped
moving average smooths the curve, and every phase keeps at least two tracks. A set that
has no journey - too short, too flat, or barely any energies - gets no phases at all and
a reason the preview can explain.
"""

from __future__ import annotations

import pytest

from xfinaudio.exporting.serato_crate_phases import EnergyPhase, EnergyPhasePlan, plan_energy_phases

# A twenty-track journey: a quiet opening, a long climb, a three-track peak, a long tail.
JOURNEY = (4, 4, 4, 4, 4, 6, 7, 8, 9, 10, 10, 10, 9, 8, 7, 6, 5, 4, 4, 4)
ASCENDING = (2, 3, 4, 5, 6, 7, 8, 9, 10, 10)
QUIET_OPENING_AND_DIP = (4, 5, 6, 7, 6, 5, 4, 5, 6, 7, 8, 9, 10, 10, 9, 8, 7, 6, 5, 4)
FLAT = (5, 6, 5, 6, 5, 6, 5, 6, 5, 6, 5, 6)


def _spans(plan: EnergyPhasePlan) -> list[tuple[int, str, int, int]]:
    return [(phase.number, phase.name, phase.first_position, phase.last_position) for phase in plan.phases]


def test_a_journey_set_splits_into_the_four_phases_in_order() -> None:
    plan = plan_energy_phases(JOURNEY)

    assert plan.reason is None
    assert _spans(plan) == [
        (1, "Apertura", 1, 4),
        (2, "Subida", 5, 9),
        (3, "Pico", 10, 12),
        (4, "Cierre", 13, 20),
    ]
    assert [phase.track_count for phase in plan.phases] == [4, 5, 3, 8]
    # The children inherit 0-based half-open runs that cover the list without a hole.
    assert [(phase.start, phase.end) for phase in plan.phases] == [(0, 4), (4, 9), (9, 12), (12, 20)]
    assert [phase.label for phase in plan.phases] == [
        "1 Apertura (1-4)",
        "2 Subida (5-9)",
        "3 Pico (10-12)",
        "4 Cierre (13-20)",
    ]


def test_the_smoothed_curve_is_the_normalised_set_averaged_over_three_points() -> None:
    plan = plan_energy_phases(JOURNEY)

    # Normalised to the list's own 4..10 range, then an edge-clamped (0.25, 0.5, 0.25)
    # average rounded to three decimals: the plateau of the three 10s stays a plateau.
    assert plan.curve == (
        0.0,
        0.0,
        0.0,
        0.0,
        0.083,
        0.292,
        0.5,
        0.667,
        0.833,
        0.958,
        1.0,
        0.958,
        0.833,
        0.667,
        0.5,
        0.333,
        0.167,
        0.042,
        0.0,
        0.0,
    )


def test_an_ascending_set_ends_on_its_peak_and_has_no_cierre() -> None:
    plan = plan_energy_phases(ASCENDING)

    assert plan.reason is None
    # A one-track opening is not a phase: it merges into the climb that follows it.
    assert _spans(plan) == [(1, "Subida", 1, 8), (2, "Pico", 9, 10)]
    assert "Cierre" not in [phase.name for phase in plan.phases]
    assert plan.phases[-1].end == len(ASCENDING)


def test_an_earlier_peak_folds_into_subida_and_only_the_top_one_is_the_pico() -> None:
    plan = plan_energy_phases(QUIET_OPENING_AND_DIP)

    assert _spans(plan) == [
        (1, "Subida", 1, 12),
        (2, "Pico", 13, 14),
        (3, "Cierre", 15, 20),
    ]


@pytest.mark.parametrize(
    ("energies", "reason"),
    [
        (FLAT, "flat"),
        ((5, 5, 5, 5, 5, 5, 5, 5, 5, 5), "flat"),
        (JOURNEY[:7], "too_few_tracks"),
        ((8, None, None, None, None, None, None, None, None, None), "too_few_energies"),
        ((None,) * 12, "too_few_energies"),
    ],
)
def test_a_set_without_a_journey_gets_no_phases_and_a_reason(
    energies: tuple[int | None, ...],
    reason: str,
) -> None:
    plan = plan_energy_phases(energies)

    assert plan.phases == ()
    assert plan.reason == reason
    assert plan.curve == ()


def test_a_range_of_two_steps_clears_the_flat_floor_but_alternating_energies_name_no_phase() -> None:
    # The flat floor is 0.2 of the 1-10 span: a range of one step (0.111) is flat, a range
    # of two steps (0.222) is not. Alternating energies still make one flat band, so they
    # name no phase either - and for their own reason, not the flat one.
    narrow = (4, 5, 4, 5, 4, 5, 4, 5, 4, 5, 4, 5)
    wide = (4, 6, 4, 6, 4, 6, 4, 6, 4, 6, 4, 6)

    assert plan_energy_phases(narrow).reason == "flat"
    assert plan_energy_phases(wide).reason == "single_phase"
    assert plan_energy_phases(wide).phases == ()


def test_a_missing_energy_takes_the_nearest_known_value() -> None:
    gaps = (None, None) + JOURNEY[2:10] + (None,) + JOURNEY[11:18] + (None, None)
    filled = (JOURNEY[2],) * 2 + JOURNEY[2:10] + (JOURNEY[10],) + JOURNEY[11:18] + (JOURNEY[18],) * 2

    assert len(gaps) == len(JOURNEY) == len(filled)
    assert plan_energy_phases(gaps) == plan_energy_phases(filled)


def test_the_same_ordered_set_always_gives_the_same_phases() -> None:
    first = plan_energy_phases(JOURNEY)
    second = plan_energy_phases(tuple(JOURNEY))

    assert first == second
    assert first.curve == second.curve


@pytest.mark.parametrize("energies", [JOURNEY, ASCENDING, QUIET_OPENING_AND_DIP])
def test_every_phase_holds_at_least_two_tracks_and_they_cover_the_set(
    energies: tuple[int | None, ...],
) -> None:
    plan = plan_energy_phases(energies)

    assert plan.phases
    assert all(phase.track_count >= 2 for phase in plan.phases)
    assert [phase.number for phase in plan.phases] == list(range(1, len(plan.phases) + 1))
    assert plan.phases[0].start == 0
    assert plan.phases[-1].end == len(energies)
    assert all(later.start == earlier.end for earlier, later in zip(plan.phases, plan.phases[1:], strict=False))


def test_a_phase_plan_is_immutable_and_compares_by_value() -> None:
    plan = plan_energy_phases(JOURNEY)

    with pytest.raises(ValueError):
        plan.reason = "flat"  # type: ignore[misc]
    with pytest.raises(ValueError):
        plan.phases[0].name = "Cierre"  # type: ignore[misc]

    # The models are plain values: equality is by content, so two runs compare equal.
    assert EnergyPhase(name="Apertura", number=1, start=0, end=4) == plan.phases[0]


def test_the_phase_helper_is_exported_from_the_package_api() -> None:
    from xfinaudio.exporting import EnergyPhase as exported_phase  # noqa: PLC0415
    from xfinaudio.exporting import plan_energy_phases as exported_planner  # noqa: PLC0415

    assert exported_planner is plan_energy_phases
    assert exported_phase is EnergyPhase
