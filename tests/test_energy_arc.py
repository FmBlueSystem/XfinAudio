"""Tests for the target energy shape of a set."""

from __future__ import annotations

import pytest

from xfinaudio.recommendation.energy_arc import arc_targets, normalized_arc_position


def test_journey_peaks_around_two_thirds_in() -> None:
    """The source puts the main peak about two thirds through, not at the end."""
    targets = arc_targets("harmonic_journey", length=15)

    peak_index = targets.index(max(targets))
    assert 8 <= peak_index <= 11, f"peak at {peak_index} of 15"
    assert targets[-1] < targets[peak_index]


def test_journey_starts_below_its_peak() -> None:
    targets = arc_targets("harmonic_journey", length=15)

    assert targets[0] < targets[len(targets) // 2]


def test_warmup_climbs_all_the_way() -> None:
    """A warm-up hands over hot; it never comes back down."""
    targets = arc_targets("warmup", length=12)

    assert targets == sorted(targets)
    assert targets[-1] > targets[0]


def test_peak_time_stays_high_throughout() -> None:
    targets = arc_targets("peak_time", length=12)

    assert min(targets) >= 0.75
    assert max(targets) - min(targets) <= 0.25


def test_chill_stays_low_and_flat() -> None:
    targets = arc_targets("chill", length=12)

    assert max(targets) <= 0.35
    assert max(targets) - min(targets) <= 0.2


def test_same_energy_is_deliberately_flat() -> None:
    """Holding one level is the whole point of the strategy."""
    targets = arc_targets("same_energy", length=12)

    assert max(targets) - min(targets) == pytest.approx(0.0)


def test_targets_are_normalised_between_zero_and_one() -> None:
    for name in ("harmonic_journey", "warmup", "build", "peak_time", "chill", "same_energy"):
        targets = arc_targets(name, length=10)
        assert all(0.0 <= value <= 1.0 for value in targets), name


def test_length_of_one_is_handled() -> None:
    assert len(arc_targets("harmonic_journey", length=1)) == 1


def test_position_is_normalised_across_the_set() -> None:
    assert normalized_arc_position(0, 10) == pytest.approx(0.0)
    assert normalized_arc_position(9, 10) == pytest.approx(1.0)
    assert normalized_arc_position(0, 1) == pytest.approx(0.0)


def test_journey_can_start_from_where_the_anchor_already_sits() -> None:
    """The anchor is fixed at slot zero; the curve has to build from it.

    With an absolute curve, a high-energy anchor made the set descend from its
    own opening -- on the real library the peak landed at 5% of the way through
    instead of 68%, because the shape wanted a quiet start the anchor could not
    provide.
    """
    high = arc_targets("harmonic_journey", length=15, start_at=0.8)

    assert high[0] == pytest.approx(0.8)
    assert max(high) > high[0], "a set anchored high should still build"
    assert high.index(max(high)) > len(high) // 2


def test_anchored_curve_still_releases_at_the_end() -> None:
    targets = arc_targets("harmonic_journey", length=15, start_at=0.8)

    assert targets[-1] < max(targets)


def test_start_at_is_ignored_by_flat_shapes() -> None:
    """same_energy holds a level on purpose; an anchor does not change that."""
    targets = arc_targets("same_energy", length=10, start_at=0.9)

    assert max(targets) - min(targets) == pytest.approx(0.0)
