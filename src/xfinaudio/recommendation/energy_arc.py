"""Target energy shape for a set, as a curve over its running order.

The optimizer scores adjacent transitions, and energy scores highest when two
tracks share a level. Maximizing that sum therefore rewards never changing the
energy at all: measured on a real library, generated sets spanned 2.2 levels out
of 10, and one ran 25 tracks without leaving level 7.

That is the algorithm doing exactly what it was asked. A set is not a chain of
good pairs, it is a shape over time -- the sources describe a main peak about
two thirds in, energy rising in steps rather than at every transition, and a
release at the end. This module says what that shape should be; the optimizer
scores adherence to it alongside transition quality.

Targets are normalized 0-1 rather than expressed as energy levels, so a set
built from a pool that only spans levels 5-8 still traces the full shape within
the range it actually has.
"""

from __future__ import annotations

# Where the main peak sits, as a fraction of the way through the set. The
# sources put it around two thirds, leaving room for a release afterwards.
_PEAK_POSITION = 0.68
# How high a journey opens and closes, relative to its own peak.
_JOURNEY_START = 0.35
_JOURNEY_END = 0.55
# A journey has to climb noticeably above its opening to read as a build, even
# when the anchor already sits high in the range the pool offers.
_MIN_CLIMB = 0.4


def normalized_arc_position(index: int, length: int) -> float:
    """Return where a slot sits in the set, from 0.0 at the open to 1.0 at the close."""
    if length <= 1:
        return 0.0
    return index / (length - 1)


def _journey(position: float, start: float = _JOURNEY_START) -> float:
    """Rise to a peak about two thirds in, then release.

    ``start`` is where the set actually opens. The anchor is fixed at slot zero
    and the DJ picked it, so the shape builds from wherever that lands instead
    of asking for a quiet opening the anchor cannot give. The peak stays a
    genuine climb above the opening even when the anchor is already loud.
    """
    # min, not max: letting the peak exceed 1.0 and clamping afterwards turns
    # the top of the curve into a plateau, which moves the peak earlier.
    peak = min(1.0, start + _MIN_CLIMB)
    if position <= _PEAK_POSITION:
        climbed = position / _PEAK_POSITION
        return start + (peak - start) * climbed
    fallen = (position - _PEAK_POSITION) / (1.0 - _PEAK_POSITION)
    release = start + (peak - start) * _JOURNEY_END
    return peak - (peak - release) * fallen


def _ascending(position: float, start: float = 0.25) -> float:
    """Open where the anchor sits and hand over hot, without coming back down.

    The opening is capped so the curve always has somewhere to climb. An anchor
    at the top of the pool's range normalizes to 1.0, and ``start + (1.0 -
    start) * position`` is a constant 1.0 from there: every slot asks for
    maximum energy, nothing separates the candidates, and the arc term goes
    inert -- which hands the set back to the transition score, whose favourite
    move is never changing energy at all. Six warmup sets measured on the real
    library came out like ``[7, 3, 3, 3, ... 3]``.

    Capping costs nothing where it applies. Slot zero belongs to the anchor
    whatever this returns, so the cap only shapes the slots actually being
    chosen.
    """
    opening = min(start, 1.0 - _MIN_CLIMB)
    return opening + (1.0 - opening) * position


def _sustained_high(position: float, start: float = 0.85) -> float:
    """Hold near the top; peak-time sets do not build, they stay."""
    return 0.85 + 0.15 * (1.0 - abs(position - 0.5) * 2.0)


def _low_and_flat(position: float, start: float = 0.25) -> float:
    return 0.25


def _flat(position: float, start: float = 0.5) -> float:
    """No shape at all -- the strategy is about holding one level."""
    return start


_ARCS = {
    "harmonic_journey": _journey,
    "warmup": _ascending,
    "build": _ascending,
    "peak_time": _sustained_high,
    "chill": _low_and_flat,
    "same_energy": _flat,
    "same_color_energy": _flat,
}


def arc_targets(strategy_name: str, *, length: int, start_at: float | None = None) -> list[float]:
    """Return the normalized target energy for each slot of a set.

    ``start_at`` is where the set actually opens, normalized against the pool's
    energy range. Shapes that build use it as their opening; flat shapes ignore
    it, since holding one level is their entire point.

    Strategies with no documented shape get a flat curve, which makes the arc
    term inert for them rather than imposing one.
    """
    shape = _ARCS.get(strategy_name, _flat)
    positions = [normalized_arc_position(index, max(length, 1)) for index in range(max(length, 1))]
    if start_at is None:
        return [shape(position) for position in positions]
    anchored = min(max(start_at, 0.0), 1.0)
    return [min(1.0, shape(position, anchored)) for position in positions]


def traces_an_arc(strategy_name: str) -> bool:
    """Return whether this strategy wants a shape rather than a held level.

    Callers use it to decide whether the candidate pool should spread across
    energy levels: a shape needs material at both ends, a held level does not.
    """
    return _ARCS.get(strategy_name, _flat) not in (_flat, _low_and_flat)


__all__ = ["arc_targets", "normalized_arc_position", "traces_an_arc"]
