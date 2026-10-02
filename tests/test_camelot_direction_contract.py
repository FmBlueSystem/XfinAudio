"""Truth table sourced from Mixed In Key's advanced harmonic mixing guide."""

import pytest

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.camelot import score_camelot_transition
from xfinaudio.recommendation.scoring import score_transition


@pytest.mark.parametrize("number", range(1, 13))
@pytest.mark.parametrize("letter", ["A", "B"])
def test_diagonal_respects_mode_direction(number: int, letter: str) -> None:
    source = f"{number}{letter}"
    other = "B" if letter == "A" else "A"
    step = -1 if letter == "A" else 1
    compatible = f"{(number - 1 + step) % 12 + 1}{other}"
    clashing = f"{(number - 1 - step) % 12 + 1}{other}"
    assert score_camelot_transition(source, compatible) == 0.9
    assert score_camelot_transition(source, clashing) == 0.0
    assert score_camelot_transition(source, clashing, boost_rules={(source, clashing)}) == 0.8


@pytest.mark.parametrize("destination,interval", [("3A", "semitone"), ("10A", "whole step")])
def test_boost_explanation_names_actual_interval(destination: str, interval: str) -> None:
    left = TrackRecord(path="a", bpm=120, camelot_key="8A", energy_level=5, metadata_status="complete")
    right = left.model_copy(update={"path": "b", "camelot_key": destination})
    result = score_transition(left, right)
    boost = next(text for text in result.explanations if text.startswith("Energy boost"))
    assert interval in boost
    assert "cut rather than blend" in boost
