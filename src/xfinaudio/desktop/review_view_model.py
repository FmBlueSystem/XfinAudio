"""ReviewViewModel — transforms AppState into display data for the Review Mix screen.

The readiness semaphore (READY / NEEDS_REVIEW / BLOCKED) is the primary output.
A BLOCKED status disables export.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from xfinaudio.desktop.app_state import AppState


class ReadinessStatus(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class ReadinessCheckRow:
    label: str
    status: str  # "ready" | "needs_review" | "blocked"
    detail: str


@dataclass(frozen=True)
class TransitionRow:
    from_track: str
    to_track: str
    score: str  # formatted as "0.85"
    has_warning: bool
    warning_text: str  # "" if no warning


@dataclass(frozen=True)
class RecommendationRow:
    position: int  # 1-indexed
    title: str
    artist: str
    bpm: str  # "128" or "—"
    camelot_key: str  # "8A" or "—"
    energy: str  # "7" or "—"
    overall_score: str  # "0.92" or "—"
    path: str = ""


class ReviewViewModel:
    """Pure-Python ViewModel for the Review Mix screen. No PySide6 dependency."""

    def readiness_status(self, state: AppState) -> ReadinessStatus:
        """Primary semaphore output.

        - No recommendation → BLOCKED
        - All tracks removed → BLOCKED
        - Recommendation but no readiness report → NEEDS_REVIEW
        - Readiness report present → map its status directly
        """
        if state.last_recommendation is None:
            return ReadinessStatus.BLOCKED
        remaining = [t for t in state.last_recommendation.ordered_tracks if t.path not in state.playlist_removed_paths]
        if not remaining:
            return ReadinessStatus.BLOCKED
        if state.last_dj_readiness_report is None:
            return ReadinessStatus.NEEDS_REVIEW
        report_status = state.last_dj_readiness_report.status
        if report_status == "blocked":
            return ReadinessStatus.BLOCKED
        if report_status == "needs_review":
            return ReadinessStatus.NEEDS_REVIEW
        return ReadinessStatus.READY

    def readiness_badge_text(self, state: AppState) -> str:
        """Human-readable badge label matching the semaphore state."""
        status = self.readiness_status(state)
        if state.last_recommendation is None:
            return "No playlist generated"
        if status == ReadinessStatus.BLOCKED:
            return "Blocked: do not export yet"
        if status == ReadinessStatus.NEEDS_REVIEW:
            return "Needs review before export"
        return "Ready to export"

    def readiness_checks(self, state: AppState) -> list[ReadinessCheckRow]:
        """Flat list of check rows from the DJ readiness report. Empty if no report."""
        if state.last_dj_readiness_report is None:
            return []
        return [
            ReadinessCheckRow(
                label=check.label,
                status=check.status,
                detail=check.detail,
            )
            for check in state.last_dj_readiness_report.checks
        ]

    def transition_rows(self, state: AppState) -> list[TransitionRow]:
        """Transition rows from the playlist explanation. Empty if no explanation."""
        if state.last_playlist_explanation is None:
            return []
        rows: list[TransitionRow] = []
        for transition in state.last_playlist_explanation.transitions:
            from_title = transition.left.title or transition.left.path
            to_title = transition.right.title or transition.right.path
            has_warning = bool(transition.warnings)
            warning_text = "; ".join(transition.warnings) if has_warning else ""
            rows.append(
                TransitionRow(
                    from_track=from_title,
                    to_track=to_title,
                    score=f"{transition.final_score:.2f}",
                    has_warning=has_warning,
                    warning_text=warning_text,
                )
            )
        return rows

    def quality_summary(self, state: AppState) -> str:
        """One-line quality summary. Returns '—' when no report is available."""
        report = state.last_quality_report
        if report is None:
            return "—"
        return (
            f"Avg transition score: {report.average_transition_score:.2f} "
            f"({report.transition_count} transition(s), {report.warning_count} warning(s))"
        )

    def can_export(self, state: AppState) -> bool:
        """Export is allowed for READY and NEEDS_REVIEW; BLOCKED gates it.

        Also returns False when all tracks have been removed from the playlist.
        """
        if state.last_recommendation is not None:
            remaining = [
                t for t in state.last_recommendation.ordered_tracks if t.path not in state.playlist_removed_paths
            ]
            if not remaining:
                return False
        return self.readiness_status(state) != ReadinessStatus.BLOCKED

    def recommendation_rows(self, state: AppState) -> list[RecommendationRow]:
        """Track rows for the recommendation table. Empty if no recommendation.

        Tracks in playlist_removed_paths are excluded from the output.
        """
        if state.last_recommendation is None:
            return []
        rows: list[RecommendationRow] = []
        position = 1
        for track in state.last_recommendation.ordered_tracks:
            if track.path in state.playlist_removed_paths:
                continue
            bpm_str = str(int(track.bpm)) if track.bpm is not None else "—"
            key_str = track.camelot_key if track.camelot_key is not None else "—"
            energy_str = str(track.energy_level) if track.energy_level is not None else "—"
            rows.append(
                RecommendationRow(
                    position=position,
                    title=track.title or track.path,
                    artist=track.artist or "—",
                    bpm=bpm_str,
                    camelot_key=key_str,
                    energy=energy_str,
                    overall_score="—",  # score not available at track level
                    path=track.path,
                )
            )
            position += 1
        return rows


__all__ = [
    "ReadinessCheckRow",
    "ReadinessStatus",
    "RecommendationRow",
    "ReviewViewModel",
    "TransitionRow",
]
