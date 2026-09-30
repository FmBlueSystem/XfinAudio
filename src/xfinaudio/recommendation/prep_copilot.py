"""DJ prep copilot planning helpers.

This module turns a DJ set intent into a small set of comparable playlist
variants. It keeps the human DJ in control: intent and hard gates lead; the
algorithm only proposes auditable options.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation import candidate_pool
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.familiarity import FamiliaritySignal
from xfinaudio.recommendation.loudness_policy import DEFAULT_LOUDNESS_BAND, LoudnessBand
from xfinaudio.recommendation.playlist_service import (
    PlaylistRecommendation,
    matches_requested_genre,
    matches_requested_genre_tag,
    recommend_playlist,
    recommendation_limited,
)
from xfinaudio.recommendation.strategies import StrategyName

if TYPE_CHECKING:
    from xfinaudio.quality.dj_readiness import DjReadinessCheck, DjReadinessReport  # noqa: F401
    from xfinaudio.quality.recommendation_quality import RecommendationQualityReport  # noqa: F401

PrepVariantName = Literal["safe", "balanced", "adventurous"]
# How long each track is on air before the mix moves on, matching the desktop
# Build screen's slot sizing (``DESKTOP_PLAYED_SECONDS_PER_TRACK`` in
# ``desktop/recommendation_service.py``). A DJ plays a segment, not the whole
# record: at a 4.8 minute median a 30-minute slot is 6 tracks played whole but
# 15 played two minutes at a time.
PREP_PLAYED_SECONDS_PER_TRACK = 120.0


class DJSetIntent(BaseModel):
    """Human DJ intent for preparing a focused playlist candidate set."""

    model_config = ConfigDict(frozen=True)

    name: str
    strategy: StrategyName | str = "harmonic_journey"
    target_track_count: int = Field(default=25, ge=2, le=100)
    # The booked slot length in minutes -- the number a DJ actually plans from
    # (see odd/research/dj-mixing-techniques.md T3). A fixed track count cannot
    # hit a slot: on the real library 10 tracks ran anywhere from 36 to 71
    # minutes. Optional so older serialized intents stay valid; when set it sizes
    # the set by runtime and ``target_track_count`` then acts only as a hard cap.
    target_minutes: float | None = Field(default=None, gt=0, le=600)
    # Which part of the night this set plays (T4), decoupled from ``strategy``:
    # the strategy still weights, filters and orders the set, while the slot role
    # names the energy SHAPE traced underneath -- a warm-up arc over
    # harmonic_journey ordering, for example. These are the existing arc-capable
    # curve names in ``energy_arc._ARCS`` (no new curves). Optional so older
    # serialized intents stay valid; ``None`` keeps the legacy coupling where the
    # strategy's own curve applies.
    slot_role: Literal["warmup", "peak_time", "chill"] | None = None
    start_path: str | None = None
    end_path: str | None = None
    required_paths: list[str] = Field(default_factory=list)
    excluded_paths: set[str] = Field(default_factory=set)
    genre_focus: str | None = None
    # Diagnostics preamble recorded by the caller BEFORE the plan ran (e.g. a
    # desktop genre prefilter), prepended to every variant's pool notes so the
    # Tracks tooltip explains shrink steps upstream of the incoming pool.
    # Optional so older serialized intents stay valid.
    pool_note_preamble: str | None = None


class PrepCopilotVariant(BaseModel):
    """One comparable DJ prep option for the same set intent."""

    model_config = ConfigDict(frozen=True)

    name: PrepVariantName
    description: str
    recommendation: PlaylistRecommendation
    readiness: DjReadinessReport
    warnings: list[str]
    blockers: list[str]
    # HOW the candidate pool shrank on the way to this variant (incoming size,
    # genre-filter result, BPM-gate drops). Tuple with a safe default so older
    # serialized plans and state transitions stay valid; the Build UI shows it
    # as the Tracks-cell tooltip so a 1-track variant is never unexplained.
    pool_notes: tuple[str, ...] = ()


class PrepCopilotPlan(BaseModel):
    """Three-option prep plan generated from one DJ set intent."""

    model_config = ConfigDict(frozen=True)

    intent: DJSetIntent
    variants: list[PrepCopilotVariant]


def build_prep_copilot_plan(
    tracks: list[TrackRecord],
    intent: DJSetIntent,
    *,
    color_anchor_path: str | None = None,
    loudness_band: LoudnessBand = DEFAULT_LOUDNESS_BAND,
    familiarity: Mapping[str, FamiliaritySignal] | None = None,
    familiarity_weight: float = 0.0,
) -> PrepCopilotPlan:
    """Build safe, balanced, and adventurous playlist variants for one DJ set intent.

    ``color_anchor_path`` is the colour-gate anchor identity already bound by the
    candidate-planning seam. It stays a parameter rather than a `DJSetIntent` field:
    the intent models what the human asked for, the anchor path is machine-bound
    identity. Every variant gates against that exact track, so a variant filter that
    removes it fails closed instead of rebinding a different anchor.

    ``familiarity``/``familiarity_weight`` pass the opt-in Serato preference
    signal (Plan 3 T3) through to `build_recommendation_pool`. INERT BY
    DEFAULT: callers omit them (or pass weight 0) unless the Serato
    integration is enabled and actually yielded data. Familiarity only
    reorders the candidate pool; it never blocks a track.
    """
    from xfinaudio.quality.dj_readiness import DjReadinessReport  # noqa: F401

    PrepCopilotVariant.model_rebuild()
    variants = [
        _build_variant(
            "safe",
            tracks,
            intent,
            color_anchor_path=color_anchor_path,
            loudness_band=loudness_band,
            familiarity=familiarity,
            familiarity_weight=familiarity_weight,
        ),
        _build_variant(
            "balanced",
            tracks,
            intent,
            color_anchor_path=color_anchor_path,
            loudness_band=loudness_band,
            familiarity=familiarity,
            familiarity_weight=familiarity_weight,
        ),
        _build_variant(
            "adventurous",
            tracks,
            intent,
            color_anchor_path=color_anchor_path,
            loudness_band=loudness_band,
            familiarity=familiarity,
            familiarity_weight=familiarity_weight,
        ),
    ]
    return PrepCopilotPlan(intent=intent, variants=variants)


def _build_variant(
    name: PrepVariantName,
    tracks: list[TrackRecord],
    intent: DJSetIntent,
    *,
    color_anchor_path: str | None = None,
    loudness_band: LoudnessBand = DEFAULT_LOUDNESS_BAND,
    familiarity: Mapping[str, FamiliaritySignal] | None = None,
    familiarity_weight: float = 0.0,
) -> PrepCopilotVariant:
    """Build one prep variant from the intent.

    Precedence between the two size limits: ``target_minutes`` is the booked slot
    and sizes the set by runtime (with ``PREP_PLAYED_SECONDS_PER_TRACK`` as the
    on-air segment). When both fields are set the minutes budget wins for sizing
    and ``target_track_count`` only cuts the result down to a hard cap, so a DJ
    who names both gets a set that fits the slot without exceeding the count.
    With no ``target_minutes`` the legacy count trim is the only limit.

    ``slot_role`` is forwarded as ``arc_strategy`` while ``strategy`` stays the
    ordering strategy, decoupling the shape from the ordering (T4).
    """
    from xfinaudio.quality.dj_readiness import build_dj_readiness_report
    from xfinaudio.quality.recommendation_quality import build_quality_report

    incoming_count = len(tracks)
    variant_tracks, variant_warnings = _filter_tracks_for_variant(name, tracks, intent)
    controls = DJControls(
        start_path=intent.start_path,
        end_path=intent.end_path,
        manual_order_paths=_manual_order_paths(intent),
        excluded_paths=intent.excluded_paths,
    )
    # Without an anchor-narrowed pool, the optimizer receives a scattered BPM
    # sample and the 3% adjacency gate can leave only the anchor behind.
    recommendation_pool = candidate_pool.build_recommendation_pool(
        [track for track in variant_tracks if track.path not in intent.excluded_paths],
        controls,
        limit=max(25, intent.target_track_count),
        protected_path=color_anchor_path,
        familiarity=familiarity,
        familiarity_weight=familiarity_weight,
    )
    recommendation = recommend_playlist(
        recommendation_pool,
        intent.strategy,
        controls=controls,
        color_anchor_path=color_anchor_path,
        loudness_band=loudness_band,
        target_count=intent.target_track_count,
        target_duration_minutes=intent.target_minutes,
        played_seconds_per_track=(PREP_PLAYED_SECONDS_PER_TRACK if intent.target_minutes is not None else None),
        arc_strategy=intent.slot_role,
    )
    recommendation = _limit_recommendation(recommendation, intent.target_track_count)
    readiness = build_dj_readiness_report(recommendation, build_quality_report(recommendation))
    readiness = _add_required_track_gate(readiness, recommendation, intent)
    blockers = [check.label for check in readiness.checks if check.status == "blocked"]
    # Pool diagnostics: the same BPM-gate drop warnings the DJ already gets,
    # restated as pool-shrink steps so the Tracks count is never unexplained.
    # The preamble leads because it describes a shrink that happened BEFORE this
    # pool was assembled (e.g. the desktop Build genre prefilter).
    pool_notes = [
        *([intent.pool_note_preamble] if intent.pool_note_preamble else []),
        f"Incoming pool: {incoming_count} track(s)",
        _genre_filter_pool_note(name, intent, incoming_count, len(variant_tracks)),
        *(warning for warning in recommendation.warnings if "Dropped" in warning and "BPM jump" in warning),
    ]
    warnings = [*variant_warnings, *recommendation.warnings]
    near_empty_warning = _near_empty_pool_warning(
        recommendation.ordered_tracks,
        incoming_count,
        genre_filter_shrank=len(variant_tracks) != incoming_count,
        target_track_count=intent.target_track_count,
        color_anchor_path=color_anchor_path,
    )
    if near_empty_warning is not None:
        warnings.append(near_empty_warning)
        pool_notes.append(near_empty_warning)
    return PrepCopilotVariant(
        name=name,
        description=_variant_description(name),
        recommendation=recommendation,
        readiness=readiness,
        warnings=warnings,
        blockers=blockers,
        pool_notes=tuple(pool_notes),
    )


def _filter_tracks_for_variant(
    name: PrepVariantName, tracks: list[TrackRecord], intent: DJSetIntent
) -> tuple[list[TrackRecord], list[str]]:
    """Narrow the incoming pool to this variant's genre contract, or explain why not.

    Shares the ONE genre contract with the Build genre prefilter
    (`matches_requested_genre`): casefolded whole-string equality, so a focus
    like "classical" matches a "Classical" track. Unlike the prefilter, a
    zero-match focus falls back to the incoming pool WITH a warning instead of
    silently shrinking the pool to the protected paths (the anchor when nothing
    else was selected) -- that silent shrink was the 1-track variant bug.
    """
    if intent.genre_focus is None:
        return tracks, []
    if name == "adventurous":
        return tracks, [f"adventurous variant may bridge outside genre focus: {intent.genre_focus}"]
    protected = _protected_paths(intent)
    balanced = name == "balanced"

    def _matches(track: TrackRecord) -> bool:
        return matches_requested_genre(track, intent.genre_focus) or (
            balanced and matches_requested_genre_tag(track.tags, intent.genre_focus)
        )

    focused = [track for track in tracks if track.path in protected or _matches(track)]
    if not any(_matches(track) for track in tracks):
        return tracks, [f"No tracks match genre focus '{intent.genre_focus}'; keeping the full candidate pool"]
    return focused, []


def _genre_filter_pool_note(name: PrepVariantName, intent: DJSetIntent, before: int, after: int) -> str:
    """Describe the genre-focus step of the pool shrinkage for the pool notes."""
    if intent.genre_focus is None:
        return "Genre focus: none set"
    if name == "adventurous":
        return f"Genre focus '{intent.genre_focus}': not applied (bridging allowed)"
    dropped = before - after
    if dropped:
        return f"Genre focus '{intent.genre_focus}': {before} -> {after} track(s), {dropped} outside focus"
    return f"Genre focus '{intent.genre_focus}': matched all {after} track(s)"


def _near_empty_pool_warning(
    ordered_tracks: list[TrackRecord],
    incoming_count: int,
    *,
    genre_filter_shrank: bool,
    target_track_count: int,
    color_anchor_path: str | None,
) -> str | None:
    """Explain a variant that collapsed to (almost) only its anchor.

    Fires when the variant kept at most one non-anchor track while the DJ asked
    for more, and the requested cap was not the binding constraint: meeting the
    requested track count is the contract working, not a collapse. The pool may
    already have arrived narrowed (a 1-match genre corner upstream), so the
    incoming count is reported, not required to be larger.
    """
    kept = len(ordered_tracks)
    non_anchor = sum(1 for track in ordered_tracks if track.path != color_anchor_path)
    if non_anchor > 1 or kept >= target_track_count:
        return None
    if genre_filter_shrank:
        return f"Genre focus matched only the anchor: kept {kept} of {incoming_count} pool track(s) after all gates"
    return f"Only the anchor survived the gates: kept {kept} of {incoming_count} pool track(s)"


def _manual_order_paths(intent: DJSetIntent) -> list[str]:
    paths: list[str] = []
    if intent.start_path is not None:
        paths.append(intent.start_path)
    paths.extend(path for path in intent.required_paths if path not in paths)
    return paths


def _protected_paths(intent: DJSetIntent) -> set[str]:
    protected = set(intent.required_paths)
    if intent.start_path is not None:
        protected.add(intent.start_path)
    if intent.end_path is not None:
        protected.add(intent.end_path)
    return protected


def _limit_recommendation(recommendation: PlaylistRecommendation, target_track_count: int) -> PlaylistRecommendation:
    return recommendation_limited(recommendation, target_track_count)


def _add_required_track_gate(
    readiness: DjReadinessReport, recommendation: PlaylistRecommendation, intent: DJSetIntent
) -> DjReadinessReport:
    from xfinaudio.quality.dj_readiness import DjReadinessCheck, DjReadinessReport

    required_paths = set(intent.required_paths)
    if not required_paths:
        return readiness
    recommended_paths = {track.path for track in recommendation.ordered_tracks}
    missing_required_count = len(required_paths - recommended_paths)
    if missing_required_count == 0:
        checks = [
            *readiness.checks,
            DjReadinessCheck(
                label="Required tracks",
                status="ready",
                detail="All required tracks are present in the playlist variant",
            ),
        ]
    else:
        missing_check = DjReadinessCheck(
            label="Required tracks",
            status="blocked",
            detail=f"{missing_required_count} required track(s) could not pass playlist gates",
        )
        if any("BPM jump" in warning or "BPM ceiling" in warning for warning in recommendation.warnings):
            bpm_check = DjReadinessCheck(
                label="BPM continuity",
                status="blocked",
                detail="A required transition cannot satisfy the adjacent BPM gate",
            )
            checks = [*readiness.checks, bpm_check, missing_check]
        else:
            checks = [*readiness.checks, missing_check]
    blocker_count = sum(1 for item in checks if item.status == "blocked")
    review_count = sum(1 for item in checks if item.status == "needs_review")
    status = "blocked" if blocker_count else "needs_review" if review_count else "ready"
    summary = readiness.summary
    if status == "blocked" and readiness.status != "blocked":
        summary = f"Blocked — {blocker_count} blocker(s), {review_count} review item(s); required tracks missing"
    return DjReadinessReport(
        status=status,
        summary=summary,
        checks=checks,
        blocker_count=blocker_count,
        review_count=review_count,
    )


def _variant_description(name: PrepVariantName) -> str:
    return {
        "safe": "Strictest option: stays close to the requested genre focus and hard gates.",
        "balanced": "Middle option: allows tagged bridges while preserving the set intent.",
        "adventurous": "Exploratory option: allows broader bridges but keeps readiness checks visible.",
    }[name]


__all__ = [
    "DJSetIntent",
    "PrepCopilotPlan",
    "PrepCopilotVariant",
    "PrepVariantName",
    "build_prep_copilot_plan",
]


def _ensure_prep_copilot_variant_model() -> None:
    """Resolve the forward reference for PrepCopilotVariant.readiness at import time.

    This is kept at module end to avoid a circular import while still letting
    downstream code construct PrepCopilotVariant directly.
    """
    if PrepCopilotVariant.__pydantic_complete__:
        return
    from xfinaudio.quality.dj_readiness import DjReadinessReport  # noqa: F401

    PrepCopilotVariant.model_rebuild()


_ensure_prep_copilot_variant_model()
