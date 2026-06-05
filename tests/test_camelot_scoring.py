import pytest

from xfinaudio.recommendation.camelot import CamelotKey, parse_camelot_key, score_camelot_transition


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
        ("11B", "12A", 0.7),
        ("11B", "10A", 0.7),
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
