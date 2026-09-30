"""Offline explanations and comparisons of already-computed engine results."""

from __future__ import annotations

from xfinaudio.desktop.app_state import AppState
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation


def _average(recommendation: PlaylistRecommendation) -> float:
    scores = recommendation.transition_scores
    return sum(score.total_score for score in scores) / len(scores) if scores else 0.0


def review_engine_facts(state: AppState) -> str:
    """Describe local facts; compare variants only while their context is current."""
    recommendation = state.last_recommendation
    readiness = state.last_dj_readiness_report
    if recommendation is None or readiness is None:
        return ""
    lines = [
        f"Local engine: {len(recommendation.ordered_tracks)} tracks; "
        f"average transition score {_average(recommendation):.2f}",
        readiness.summary,
    ]
    lines.extend(f"{check.label}: {check.detail}" for check in readiness.checks if check.status != "ready")
    # Keep the panel focused on the three weakest measured transitions. The
    # transition table remains the complete, selectable account of every score.
    weakest = sorted(enumerate(recommendation.transition_scores, 1), key=lambda item: item[1].total_score)[:3]
    for index, score in weakest:
        details = "; ".join([*score.explanations, *score.warnings]) or "No engine warnings"
        lines.append(f"Transition {index}: {score.total_score:.2f}; {details}")
    plan = state.last_prep_copilot_plan
    variants = [] if plan is None else plan.variants
    if not any(variant.recommendation is recommendation for variant in variants):
        variants = []
    comparisons = []
    for variant in variants:
        paths = {track.path for track in variant.recommendation.ordered_tracks}
        if paths & state.excluded_paths or not state.locked_paths <= paths:
            continue
        average = _average(variant.recommendation)
        comparisons.append(
            f"{variant.name}: {len(paths)} tracks; average score {average:.2f} "
            f"({average - _average(recommendation):+.2f}); {variant.readiness.status}; "
            f"{variant.readiness.blocker_count} blockers, {variant.readiness.review_count} review items"
        )
    lines.append("Engine-validated alternatives (comparison only):" if comparisons else "No alternative for this set.")
    lines.extend(comparisons)
    return "\n".join(lines)
