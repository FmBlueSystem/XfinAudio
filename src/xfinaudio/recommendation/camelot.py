"""Camelot wheel parsing and harmonic transition scoring."""

from __future__ import annotations

import re
from collections.abc import Collection
from typing import Literal, NamedTuple

from pydantic import BaseModel, ConfigDict

CamelotLetter = Literal["A", "B"]
BoostRule = tuple[str, str]

_KEY_PATTERN = re.compile(r"^(?P<number>1[0-2]|[1-9])(?P<letter>[abAB])$")


class CamelotKey(BaseModel):
    """Parsed Camelot wheel key."""

    model_config = ConfigDict(frozen=True)

    number: int
    letter: CamelotLetter

    def normalized(self) -> str:
        """Return the normalized Camelot key string."""
        return f"{self.number}{self.letter}"


class _Move(NamedTuple):
    number_delta: int
    same_letter: bool


_PITCH_CLASS_BY_CAMELOT: dict[CamelotLetter, dict[int, int]] = {
    "A": {
        1: 8,
        2: 3,
        3: 10,
        4: 5,
        5: 0,
        6: 7,
        7: 2,
        8: 9,
        9: 4,
        10: 11,
        11: 6,
        12: 1,
    },
    "B": {
        1: 11,
        2: 6,
        3: 1,
        4: 8,
        5: 3,
        6: 10,
        7: 5,
        8: 0,
        9: 7,
        10: 2,
        11: 9,
        12: 4,
    },
}
_CAMELOT_NUMBER_BY_PITCH_CLASS: dict[CamelotLetter, dict[int, int]] = {
    letter: {pitch_class: number for number, pitch_class in values.items()}
    for letter, values in _PITCH_CLASS_BY_CAMELOT.items()
}


def parse_camelot_key(value: str) -> CamelotKey:
    """Parse a Camelot key such as ``11B``.

    Raises:
        ValueError: If the value is not a Camelot key from 1A through 12B.
    """
    match = _KEY_PATTERN.match(value.strip())
    if match is None:
        raise ValueError(f"Invalid Camelot key: {value!r}")
    letter: CamelotLetter = "A" if match.group("letter").upper() == "A" else "B"
    return CamelotKey(number=int(match.group("number")), letter=letter)


def shift_camelot_key(value: str, semitones: int) -> str:
    """Shift a Camelot key by chromatic semitones while preserving major/minor mode."""
    parsed = parse_camelot_key(value)
    if semitones == 0:
        return parsed.normalized()
    current_pitch_class = _PITCH_CLASS_BY_CAMELOT[parsed.letter][parsed.number]
    shifted_pitch_class = (current_pitch_class + semitones) % 12
    shifted_number = _CAMELOT_NUMBER_BY_PITCH_CLASS[parsed.letter][shifted_pitch_class]
    return CamelotKey(number=shifted_number, letter=parsed.letter).normalized()


def score_camelot_transition(
    from_key: str,
    to_key: str,
    boost_rules: Collection[BoostRule] | None = None,
) -> float:
    """Score harmonic compatibility between two Camelot keys.

    Scores are deterministic: exact key ``1.0``, adjacent same-letter ``0.9``, relative A/B ``0.85``,
    diagonal (adjacent number, different letter) ``0.9``, configured boost ``0.8``, and incompatible ``0.0``.
    """
    left = parse_camelot_key(from_key)
    right = parse_camelot_key(to_key)

    if left == right:
        return 1.0

    move = _camelot_move(left, right)
    if move.number_delta == 1 and move.same_letter:
        return 0.9
    if move.number_delta == 0 and not move.same_letter:
        return 0.85
    if move.number_delta == 1 and not move.same_letter:
        return 0.9

    normalized_rule = (left.normalized(), right.normalized())
    if boost_rules is not None and normalized_rule in _normalized_boost_rules(boost_rules):
        return 0.8

    return 0.0


def _normalized_boost_rules(boost_rules: Collection[BoostRule]) -> set[BoostRule]:
    return {
        (parse_camelot_key(left).normalized(), parse_camelot_key(right).normalized()) for left, right in boost_rules
    }


def _camelot_move(left: CamelotKey, right: CamelotKey) -> _Move:
    direct_delta = abs(left.number - right.number)
    wrapped_delta = 12 - direct_delta
    return _Move(number_delta=min(direct_delta, wrapped_delta), same_letter=left.letter == right.letter)
