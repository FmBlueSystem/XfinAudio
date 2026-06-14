"""Pure-Python state machine for the Live Assistant mode.

No Qt dependency. Fully unit-testable without an event loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from xfinaudio.library.models import TrackRecord


@dataclass(frozen=True)
class SessionTrack:
    """A track that has been loaded during the live session."""

    track: TrackRecord
    loaded_at: datetime
    order: int


@dataclass(frozen=True)
class RiskAlert:
    """A visual alert for a risky transition."""

    track_path: str
    alert_type: Literal["bpm_guardrail", "key_clash", "energy_jump"]
    message: str


@dataclass(frozen=True)
class LiveAssistantState:
    """Immutable state for the Live Assistant mode."""

    current_track: TrackRecord | None = None
    candidates: list[TrackRecord] = field(default_factory=list)
    history: list[SessionTrack] = field(default_factory=list)
    alert_flags: list[RiskAlert] = field(default_factory=list)

    def set_current_track(self, track: TrackRecord) -> LiveAssistantState:
        """Set the current track without affecting history."""
        return LiveAssistantState(
            current_track=track,
            candidates=self.candidates,
            history=self.history,
            alert_flags=self.alert_flags,
        )

    def set_candidates(self, candidates: list[TrackRecord]) -> LiveAssistantState:
        """Update the candidate list."""
        return LiveAssistantState(
            current_track=self.current_track,
            candidates=candidates,
            history=self.history,
            alert_flags=self.alert_flags,
        )

    def load_next(self, track: TrackRecord, loaded_at: datetime | None = None) -> LiveAssistantState:
        """Move current track to history and set a new current track."""
        if loaded_at is None:
            loaded_at = datetime.now()

        new_history = list(self.history)
        if self.current_track is not None:
            new_history.append(
                SessionTrack(
                    track=self.current_track,
                    loaded_at=loaded_at,
                    order=len(self.history) + 1,
                )
            )

        return LiveAssistantState(
            current_track=track,
            candidates=self.candidates,
            history=new_history,
            alert_flags=self.alert_flags,
        )

    def clear(self) -> LiveAssistantState:
        """Reset to empty state."""
        return LiveAssistantState()

    def generate_alerts(self) -> list[RiskAlert]:
        """Generate risk alerts for candidates against the current track."""
        if self.current_track is None:
            return []

        alerts: list[RiskAlert] = []
        for candidate in self.candidates:
            alerts.extend(_check_candidate(self.current_track, candidate))
        return alerts


def _check_candidate(current: TrackRecord, candidate: TrackRecord) -> list[RiskAlert]:
    """Check a single candidate for risk factors."""
    alerts: list[RiskAlert] = []

    # BPM guardrail: > 3% difference
    if current.bpm is not None and candidate.bpm is not None and current.bpm > 0:
        bpm_diff = abs(candidate.bpm - current.bpm) / current.bpm
        if bpm_diff > 0.03:
            alerts.append(
                RiskAlert(
                    track_path=candidate.path,
                    alert_type="bpm_guardrail",
                    message=f"BPM +{bpm_diff * 100:.1f}%",
                )
            )

    # Key clash: not same key, not adjacent on Camelot wheel
    if (
        current.camelot_key
        and candidate.camelot_key
        and not _camelot_compatible(current.camelot_key, candidate.camelot_key)
    ):
        alerts.append(
            RiskAlert(
                track_path=candidate.path,
                alert_type="key_clash",
                message="Key clash",
            )
        )

    # Energy jump: > 2 levels
    if current.energy_level is not None and candidate.energy_level is not None:
        energy_diff = abs(candidate.energy_level - current.energy_level)
        if energy_diff > 2:
            alerts.append(
                RiskAlert(
                    track_path=candidate.path,
                    alert_type="energy_jump",
                    message=f"Energy jump -{energy_diff}",
                )
            )

    return alerts


def _camelot_compatible(left: str, right: str) -> bool:
    """Check if two Camelot keys are harmonically compatible.

    Compatible means:
    - Same key
    - Adjacent number (e.g., 11B and 12B, or 11B and 10B)
    - Same number, different letter (e.g., 11B and 11A) — relative minor/major
    """
    if left == right:
        return True

    if len(left) < 2 or len(right) < 2:
        return False

    left_num = int(left[:-1])
    left_letter = left[-1]
    right_num = int(right[:-1])
    right_letter = right[-1]

    # Same letter, adjacent number (wrap around 1-12)
    if left_letter == right_letter:
        diff = abs(left_num - right_num)
        return diff == 1 or diff == 11

    # Same number, different letter
    return left_num == right_num and left_letter != right_letter
