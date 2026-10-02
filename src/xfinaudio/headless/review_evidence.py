"""Opaque, deterministic evidence for the already-computed local recommendation."""

from __future__ import annotations

from typing import Any

from xfinaudio.application.prep_copilot import PrepCopilotVariantApplicationResult
from xfinaudio.headless.common import _public_track
from xfinaudio.recommendation.controls import DJControls, preserved_control_paths
from xfinaudio.recommendation.prep_copilot import PrepCopilotPlan


def evidence(review: PrepCopilotVariantApplicationResult, plan: PrepCopilotPlan | None) -> dict[str, Any]:
    recommendation, readiness = review.recommendation, review.readiness_report
    identities = {track.path: _public_track(track)["id"] for track in recommendation.ordered_tracks}
    transitions = [
        {
            "index": index,
            "leftTrackId": identities[score.left_path],
            "rightTrackId": identities[score.right_path],
            "totalScore": score.total_score,
            "compatibilityScore": score.compatibility_score,
            "mixabilityScore": score.mixability_score,
            "components": dict(score.component_scores),
            "explanations": list(score.explanations),
            "warnings": list(score.warnings),
        }
        for index, score in enumerate(recommendation.transition_scores, 1)
    ]
    lines = [
        f"Local engine: {len(recommendation.ordered_tracks)} tracks; "
        f"average transition score {review.quality_report.average_transition_score:.2f}",
        readiness.summary,
        *(f"{check.label}: {check.detail}" for check in readiness.checks if check.status != "ready"),
    ]
    for item in sorted(transitions, key=lambda item: item["totalScore"])[:3]:
        detail = "; ".join([*item["explanations"], *item["warnings"]]) or "No engine warnings"
        lines.append(f"Transition {item['index']}: {item['totalScore']:.2f}; {detail}")
    variants = [] if plan is None else plan.variants
    if not any(variant.recommendation is recommendation for variant in variants):
        variants = []
    lines.append("Engine-validated alternatives (comparison only):" if variants else "No alternative for this set.")
    for variant in variants:
        scores = variant.recommendation.transition_scores
        average = sum(score.total_score for score in scores) / len(scores) if scores else 0.0
        lines.append(
            f"{variant.name}: {len(variant.recommendation.ordered_tracks)} tracks; average score {average:.2f} "
            f"({average - review.quality_report.average_transition_score:+.2f}); {variant.readiness.status}; "
            f"{variant.readiness.blocker_count} blockers, {variant.readiness.review_count} review items"
        )
    return {
        "transitions": transitions,
        "protectedTrackIds": sorted(
            identities[path]
            for path in preserved_control_paths(DJControls.model_validate(recommendation.applied_controls))
            if path in identities
        ),
        "readinessChecks": [check.model_dump(mode="json") for check in readiness.checks],
        "readinessSummary": readiness.summary,
        "engineFacts": "\n".join(lines),
    }
