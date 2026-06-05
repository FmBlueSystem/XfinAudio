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


def score_camelot_transition(
    from_key: str,
    to_key: str,
    boost_rules: Collection[BoostRule] | None = None,
) -> float:
    """Score harmonic compatibility between two Camelot keys.

    Scores are deterministic: exact key ``1.0``, adjacent same-letter ``0.9``, relative A/B ``0.85``,
    diagonal fuzzy ``0.7``, configured boost ``0.8``, and incompatible ``0.0``.
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
        return 0.7

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
