"""A saved playlist opened as the list in progress, scored by the existing engine (S3).

An opened playlist is reviewed exactly like a generated list: the same payload, the
same edits. Only its plan is synthetic -- no controls, no period, no genre focus and
a single variant named ``saved`` -- because a saved list is not a generation and is
never re-planned.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, cast

from xfinaudio.application.playlist_edit_assessment import PlaylistEditAssessment, assess_playlist_edit
from xfinaudio.application.prep_copilot import (
    PrepCopilotVariantApplicationResult,
    PrepCopilotVariantLike,
    build_prep_copilot_variant_application,
)
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.prep_copilot import DJSetIntent, PrepCopilotPlan, PrepCopilotVariant

SAVED_VARIANT = "saved"
# A saved list is not sized by the intent, so the plan's own caps must accept any
# length the playlist repository stored.
MIN_PLAN_TRACK_COUNT = 2
MAX_PLAN_TRACK_COUNT = 100


@dataclass(frozen=True)
class SavedList:
    """The synthetic plan and the application result one opened playlist is bound to."""

    plan: PrepCopilotPlan
    review: PrepCopilotVariantApplicationResult

    @property
    def blockers(self) -> list[str]:
        return [check.label for check in self.review.readiness_report.checks if check.status == "blocked"]

    def variant_summary(self) -> dict[str, Any]:
        """The single variant the renderer reads, named exactly as the review names it."""
        return {
            "name": SAVED_VARIANT,
            "description": self.plan.variants[0].description,
            "trackCount": len(self.review.recommendation.ordered_tracks),
            "readiness": self.review.readiness_report.status,
            "warnings": list(self.review.recommendation.warnings),
            "blockers": self.blockers,
            "qualityScore": self.review.quality_report.average_transition_score,
        }


def assess_saved_list(tracks: Sequence[TrackRecord]) -> PlaylistEditAssessment:
    """Score the saved order with the engine a generated list is scored with."""
    return assess_playlist_edit([track.path for track in tracks], tracks)


def build_saved_list(name: str, tracks: Sequence[TrackRecord]) -> SavedList:
    """Bind the saved order to the synthetic single-variant plan a review requires.

    The engine refuses a list it cannot score (missing BPM, key or energy, or a
    blocked readiness report) with ``ValueError``; the core keeps such a playlist
    read-only instead of failing the open.
    """
    assessment = assess_saved_list(tracks)
    intent = DJSetIntent(
        name=name,
        target_track_count=min(max(len(tracks), MIN_PLAN_TRACK_COUNT), MAX_PLAN_TRACK_COUNT),
    )
    variant = PrepCopilotVariant(
        name=SAVED_VARIANT,
        description="Saved playlist: the order it was saved with, scored by the same engine.",
        recommendation=assessment.recommendation,
        readiness=assessment.readiness,
        warnings=list(assessment.recommendation.warnings),
        blockers=[check.label for check in assessment.readiness.checks if check.status == "blocked"],
    )
    return SavedList(
        plan=PrepCopilotPlan(intent=intent, variants=[variant]),
        review=build_prep_copilot_variant_application(cast(PrepCopilotVariantLike, variant)),
    )
