from pathlib import Path

import pytest

from xfinaudio.recommendation.camelot import (
    ENERGY_BOOST_SCORE,
    SEMITONE_LIFT_SCORE,
    CamelotKey,
    parse_camelot_key,
    score_camelot_transition,
)


def test_no_module_defines_a_second_camelot_compatibility_rule() -> None:
    source_root = Path(__file__).parents[1] / "src"

    matches = [
        path for path in source_root.rglob("*.py") if "def _camelot_compatible" in path.read_text(encoding="utf-8")
    ]

    assert matches == []


def test_parse_camelot_key_accepts_valid_key_case_insensitively() -> None:
    assert parse_camelot_key("11b") == CamelotKey(number=11, letter="B")


@pytest.mark.parametrize(
    ("from_key", "to_key", "expected"),
    [
        ("11B", "11B", 1.0),
        ("11B", "12B", 0.9),
        ("11B", "10B", 0.9),
        ("12A", "1A", 0.9),
        ("11B", "11A", 0.85),
        ("11B", "12A", 0.9),
        ("11B", "10A", 0.9),
        ("11B", "4A", 0.0),
    ],
)
def test_score_camelot_transition_scores_harmonic_moves(from_key: str, to_key: str, expected: float) -> None:
    assert score_camelot_transition(from_key, to_key) == expected


def test_score_camelot_transition_scores_configured_energy_boost() -> None:
    boost_rules = {("11B", "1B")}

    assert score_camelot_transition("11B", "1B", boost_rules=boost_rules) == 0.8


def test_parse_camelot_key_rejects_invalid_key() -> None:
    with pytest.raises(ValueError, match="Invalid Camelot key"):
        parse_camelot_key("13C")


@pytest.mark.parametrize(
    ("from_key", "to_key"),
    [("5A", "7A"), ("8A", "10A"), ("12A", "2A"), ("11B", "1B")],
)
def test_energy_boost_is_playable_not_a_clash(from_key: str, to_key: str) -> None:
    """+2 on the same ring is Mixed In Key's documented Energy Boost.

    It scored 0.00 -- identical to a harmonic clash -- so the optimizer, which
    maximizes adjacent scores, could never propose a lift. On a real library
    that discarded 10.7M valid pairs, 27% on top of what it accepted.
    """
    assert score_camelot_transition(from_key, to_key) == pytest.approx(ENERGY_BOOST_SCORE)


def test_energy_boost_ranks_below_the_safe_moves_and_above_a_clash() -> None:
    """It lifts the floor but needs a cut, not a long blend, so it is not a peer of +1."""
    clash = score_camelot_transition("8A", "1A")
    boost = score_camelot_transition("8A", "10A")
    adjacent = score_camelot_transition("8A", "9A")
    same = score_camelot_transition("8A", "8A")

    assert clash < boost < adjacent < same


def test_energy_boost_across_the_wheel_wrap_is_recognised() -> None:
    """Wrapping past 12 still counts, as long as the move goes up."""
    assert score_camelot_transition("12A", "2A") == pytest.approx(ENERGY_BOOST_SCORE)
    assert score_camelot_transition("11A", "1A") == pytest.approx(ENERGY_BOOST_SCORE)
    # The mirror of that wrap is a drop, not a lift.
    assert score_camelot_transition("1A", "11A") == 0.0


def test_energy_boost_requires_matching_letters() -> None:
    """A +2 that also swaps ring is not the documented technique."""
    assert score_camelot_transition("8A", "10B") == 0.0


def test_energy_boost_is_directional() -> None:
    """Only going up is the documented technique.

    The first implementation used the wheel's minimum distance, which cannot
    tell +2 from -2, so dropping a whole step scored as a lift.
    """
    assert score_camelot_transition("8A", "10A") == pytest.approx(ENERGY_BOOST_SCORE)  # up a whole step
    assert score_camelot_transition("8A", "6A") == 0.0  # down a whole step is not a boost


@pytest.mark.parametrize(("from_key", "to_key"), [("8A", "3A"), ("5A", "12A"), ("11B", "6B")])
def test_semitone_lift_is_recognised(from_key: str, to_key: str) -> None:
    """Mixed In Key's Armin van Buuren variation: -5 on the wheel, a semitone up."""
    assert score_camelot_transition(from_key, to_key) == pytest.approx(SEMITONE_LIFT_SCORE)


def test_semitone_lift_ranks_below_the_whole_step_boost() -> None:
    """A semitone clashes harder than a whole step, so it is the more daring move."""
    assert 0.0 < SEMITONE_LIFT_SCORE < ENERGY_BOOST_SCORE


def test_semitone_drop_is_not_a_lift() -> None:
    assert score_camelot_transition("3A", "8A") == 0.0
