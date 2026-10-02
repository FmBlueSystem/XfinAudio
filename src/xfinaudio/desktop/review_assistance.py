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


def preview_engine_replacement(state: AppState, selected_path: str) -> str:
    """Compare one engine-selected replacement without applying or sending it."""
    from xfinaudio.quality.dj_readiness import build_dj_readiness_report
    from xfinaudio.quality.recommendation_quality import build_quality_report
    from xfinaudio.recommendation.controls import DJControls, preserved_control_paths
    from xfinaudio.recommendation.loudness_policy import LoudnessBand
    from xfinaudio.recommendation.playlist_service import recommendation_with_replacement
    from xfinaudio.recommendation.scoring import TransitionScoringConfig, score_transition

    recommendation = state.last_recommendation
    paths = {track.path for track in recommendation.ordered_tracks} if recommendation else set()
    if recommendation is None or selected_path not in paths:
        return "Select one track from the current recommendation."
    try:
        controls = DJControls.model_validate(recommendation.applied_controls)
    except ValueError:
        return "Current set controls are invalid; regenerate the set before comparing replacements."
    if selected_path in preserved_control_paths(controls) | state.locked_paths:
        return "This track is protected by the set controls; no replacement was proposed."
    if paths & state.excluded_paths or not state.locked_paths <= paths:
        return "Current set conflicts with locks or exclusions; regenerate it before comparing replacements."
    settings = state.settings
    proposed = recommendation_with_replacement(
        recommendation,
        selected_path,
        state.scanned_records,
        locked_paths=state.locked_paths,
        excluded_paths=state.excluded_paths,
        spectral_cohesion=settings.scoring.spectral_cohesion,
        loudness_band=LoudnessBand(settings.loudness.target_lufs, settings.loudness.tolerance_lu),
    )
    replacement = next((track for track in proposed.ordered_tracks if track.path not in paths), None)
    if replacement is None or len(proposed.ordered_tracks) != len(paths):
        return "No eligible replacement passed the engine's current constraints. The set is unchanged."
    # Normalize both sides under the same current scoring settings.
    config = TransitionScoringConfig(
        weights=recommendation.strategy.weights, spectral_cohesion=settings.scoring.spectral_cohesion
    )
    scores = [
        score_transition(left, right, config=config)
        for left, right in zip(recommendation.ordered_tracks, recommendation.ordered_tracks[1:], strict=False)
    ]
    original = recommendation.model_copy(
        update={"transition_scores": scores, "total_score": sum(s.total_score for s in scores)}
    )
    lines = [f"Replacement preview: {replacement.title or '(untitled)'} — {replacement.artist or '(unknown artist)'}"]
    for label, result in (("Original", original), ("Proposed", proposed)):
        readiness = build_dj_readiness_report(result, build_quality_report(result))
        lines.append(f"{label}: average score {_average(result):.2f}; {readiness.summary}")
        lines.extend(f"{check.label}: {check.detail}" for check in readiness.checks if check.status != "ready")
    lines.append("Preview only. Review the proposed risks before changing the set; nothing has been applied.")
    return "\n".join(lines)
