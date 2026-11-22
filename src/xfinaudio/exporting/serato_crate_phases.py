"""Split an ordered set into its own energy phases: Apertura, Subida, Pico, Cierre.

The phases come from the tracks' own Mixed In Key energies (1-10), never from the
strategy or from anything the planner invented: the list is normalised to its own range,
a track without an energy takes the nearest known one, and an edge-clamped three-point
moving average smooths the curve so a single odd track cannot open a phase of its own.
The result is a pure function of the ordered energies, so the same set always splits the
same way.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict

ENERGY_MIN = 1
ENERGY_MAX = 10
# The scale the "is this set flat?" question is measured on, as the DJ reads it.
ENERGY_SPAN = ENERGY_MAX - ENERGY_MIN
# Below a two-track split there is nothing to split, and a set shorter than a short
# excursion has no journey to tell: eight tracks is the floor the preview explains.
MIN_TRACKS = 8
MIN_KNOWN_ENERGIES = 2
# A range under a fifth of the scale is a flat set, not a journey.
FLAT_RANGE = 0.2
MIN_PHASE_TRACKS = 2
# The plateau of the peak: the top of the curve within this distance of its maximum.
PLATEAU_TOLERANCE = 0.1
CURVE_PRECISION = 3
# A fixed, symmetric smoothing kernel: the track itself weighs half, its neighbours a quarter.
_SMOOTHING_WEIGHTS = (0.25, 0.5, 0.25)

PhaseName = Literal["Apertura", "Subida", "Pico", "Cierre"]
PhaseSkipReason = Literal["too_few_tracks", "too_few_energies", "flat", "single_phase"]

_Runs = list[tuple[PhaseName, int, int]]


class EnergyPhase(BaseModel):
    """One phase of the set: a half-open run of positions in the reviewed order."""

    model_config = ConfigDict(frozen=True)

    name: PhaseName
    number: int
    start: int
    end: int

    @property
    def track_count(self) -> int:
        """How many tracks the phase holds."""
        return self.end - self.start

    @property
    def first_position(self) -> int:
        """1-based position of the phase's first track."""
        return self.start + 1

    @property
    def last_position(self) -> int:
        """1-based position of the phase's last track."""
        return self.end

    @property
    def label(self) -> str:
        """The child crate leaf name: `<n> <Fase> (<first>-<last>)`."""
        return f"{self.number} {self.name} ({self.first_position}-{self.last_position})"


class EnergyPhasePlan(BaseModel):
    """The phases of one ordered set, or the reason the set has none.

    `reason` is set exactly when `phases` is empty: a set with phases never carries one.
    """

    model_config = ConfigDict(frozen=True)

    phases: tuple[EnergyPhase, ...] = ()
    reason: PhaseSkipReason | None = None
    curve: tuple[float, ...] = ()

    @property
    def usable(self) -> bool:
        """True when the set splits into phases; false when the parent is exported alone."""
        return bool(self.phases)


def plan_energy_phases(energies: Sequence[int | None]) -> EnergyPhasePlan:
    """Split one ordered set by its own energies, or say why it cannot be split.

    A set with fewer than eight tracks, fewer than two measured energies, or a range under
    a fifth of the 1-10 scale gets no phases: the export keeps the parent alone and the
    preview explains the reason.
    """
    values = tuple(energies)
    if len(values) < MIN_TRACKS:
        return EnergyPhasePlan(reason="too_few_tracks")

    known = tuple(value for value in values if value is not None)
    if len(known) < MIN_KNOWN_ENERGIES:
        return EnergyPhasePlan(reason="too_few_energies")

    lowest, highest = min(known), max(known)
    if (highest - lowest) / ENERGY_SPAN < FLAT_RANGE:
        return EnergyPhasePlan(reason="flat")

    filled = _fill_missing(values)
    curve = _smooth(tuple((value - lowest) / (highest - lowest) for value in filled))
    peak, plateau_end = _peak_plateau(curve)
    rise = _first_rise(curve, peak=peak)
    runs = _merge_short_phases(_phase_runs(rise, peak, plateau_end, len(curve)), curve)
    if len(runs) < 2:
        # Every track ended in one phase: the set has one band, not a journey.
        return EnergyPhasePlan(reason="single_phase", curve=curve)

    return EnergyPhasePlan(
        phases=tuple(
            EnergyPhase(name=name, number=number, start=start, end=end)
            for number, (name, start, end) in enumerate(runs, start=1)
        ),
        curve=curve,
    )


def _fill_missing(values: tuple[int | None, ...]) -> tuple[int, ...]:
    """Give every gap the nearest known energy before it, or the first known one after it."""
    first_known = next(value for value in values if value is not None)
    filled: list[int] = []
    previous: int | None = None
    for value in values:
        if value is not None:
            previous = value
            filled.append(value)
        else:
            filled.append(previous if previous is not None else first_known)
    return tuple(filled)


def _smooth(values: tuple[float, ...]) -> tuple[float, ...]:
    """Edge-clamped three-point moving average, rounded to three decimals."""
    before, centre, after = _SMOOTHING_WEIGHTS
    curve: list[float] = []
    for index, value in enumerate(values):
        left = values[index - 1] if index > 0 else value
        right = values[index + 1] if index + 1 < len(values) else value
        curve.append(round(before * left + centre * value + after * right, CURVE_PRECISION))
    return tuple(curve)


def _peak_plateau(curve: tuple[float, ...]) -> tuple[int, int]:
    """The `[start, end)` run of the top of the curve, around its first maximum."""
    top = max(curve)
    first = curve.index(top)
    floor = round(top - PLATEAU_TOLERANCE, CURVE_PRECISION)
    start = first
    while start > 0 and curve[start - 1] >= floor:
        start -= 1
    end = first + 1
    while end < len(curve) and curve[end] >= floor:
        end += 1
    return start, end


def _first_rise(curve: tuple[float, ...], *, peak: int) -> int:
    """Where the climb starts: the first track higher than the one before it, else the peak."""
    for index in range(1, peak + 1):
        if curve[index] > curve[index - 1]:
            return index
    return peak


def _phase_runs(rise: int, peak: int, plateau_end: int, count: int) -> _Runs:
    """The four phases as ordered runs; an empty one is not a phase and is dropped."""
    runs: _Runs = []
    if rise > 0:
        runs.append(("Apertura", 0, rise))
    if peak > rise:
        # A second, lower peak before the top one is part of the climb, not a phase.
        runs.append(("Subida", rise, peak))
    runs.append(("Pico", peak, plateau_end))
    if plateau_end < count:
        runs.append(("Cierre", plateau_end, count))
    return runs


def _merge_short_phases(runs: _Runs, curve: tuple[float, ...]) -> _Runs:
    """Merge every phase shorter than two tracks into the neighbour nearest in mean energy."""
    merged = list(runs)
    while len(merged) > 1:
        short = next((index for index, run in enumerate(merged) if run[2] - run[1] < MIN_PHASE_TRACKS), None)
        if short is None:
            break
        name, start, end = merged[short]
        short_mean = _mean(curve, start, end)
        neighbours = [index for index in (short - 1, short + 1) if 0 <= index < len(merged)]
        target = min(
            neighbours,
            key=lambda index: (abs(_mean(curve, merged[index][1], merged[index][2]) - short_mean), index),
        )
        keeper, keeper_start, keeper_end = merged[target]
        merged[target] = (keeper, min(keeper_start, start), max(keeper_end, end))
        del merged[short]
    return merged


def _mean(curve: tuple[float, ...], start: int, end: int) -> float:
    return sum(curve[start:end]) / (end - start)


__all__ = [
    "CURVE_PRECISION",
    "ENERGY_MAX",
    "ENERGY_MIN",
    "ENERGY_SPAN",
    "FLAT_RANGE",
    "MIN_KNOWN_ENERGIES",
    "MIN_PHASE_TRACKS",
    "MIN_TRACKS",
    "PLATEAU_TOLERANCE",
    "EnergyPhase",
    "EnergyPhasePlan",
    "PhaseName",
    "PhaseSkipReason",
    "plan_energy_phases",
]
