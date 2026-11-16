"""Validated public intent and real application candidate planning, without Qt."""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from typing import Any

from xfinaudio.application.recommendation_candidates import (
    plan_recommendation_candidate_context,
    plan_recommendation_candidates,
    pool_size_for_slot,
)
from xfinaudio.application.strategy_catalog import list_strategy_catalog
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.loudness_policy import DEFAULT_LOUDNESS_BAND, LoudnessBand
from xfinaudio.recommendation.playlist_service import COLOR_FILTER_STRATEGIES
from xfinaudio.recommendation.prep_copilot import (
    PREP_PLAYED_SECONDS_PER_TRACK,
    DJSetIntent,
    PrepCopilotPlan,
    build_prep_copilot_plan,
    period_keeps_track,
)

GENERATE_FIELDS = {
    "targetTrackCount",
    "name",
    "strategy",
    "targetMinutes",
    "slotRole",
    "genreFocus",
    "startTrackId",
    "endTrackId",
    "requiredTrackIds",
    "excludedTrackIds",
    "yearMin",
    "yearMax",
}
VARIANT_NAMES = ("safe", "balanced", "adventurous")


def catalog() -> dict[str, Any]:
    """Serialize only the application-owned strategy catalog's public fields."""
    return {
        "strategies": [
            {
                "name": item.name,
                "displayName": item.display_name,
                "description": item.description,
                "requiresVibeMetadata": item.requires_vibe_metadata,
            }
            for item in list_strategy_catalog()
        ]
    }


def make_intent(params: dict[str, Any], name: str, paths: dict[str, str], records: list[TrackRecord]) -> DJSetIntent:
    """Reject coercion, unknown identities, and impossible controls before planning."""
    strategy = params.get("strategy", "harmonic_journey")
    if not isinstance(strategy, str) or strategy not in {item.name for item in list_strategy_catalog()}:
        raise ValueError("Invalid strategy")
    minutes = params.get("targetMinutes")
    if "targetMinutes" in params and (
        not isinstance(minutes, (int, float))
        or isinstance(minutes, bool)
        or not 0 < minutes <= 600
        or not math.isfinite(minutes)
    ):
        raise ValueError("Slot minutes must be a finite number greater than 0 and at most 600")
    role = params.get("slotRole")
    if role is not None and (not isinstance(role, str) or role not in ("warmup", "peak_time", "chill")):
        raise ValueError("Invalid slot role")
    genre = params.get("genreFocus")
    if "genreFocus" in params and (not isinstance(genre, str) or len(genre) > 100 or "\x00" in genre):
        raise ValueError("Invalid genre focus")

    def release_year(field: str) -> int | None:
        """S16: an optional bound of the release period, 1900 to 2100."""
        if field not in params:
            return None
        value = params[field]
        if not isinstance(value, int) or isinstance(value, bool) or not 1900 <= value <= 2100:
            raise ValueError("A release year must be an integer from 1900 to 2100")
        return value

    year_min, year_max = release_year("yearMin"), release_year("yearMax")
    if year_min is not None and year_max is not None and year_min > year_max:
        raise ValueError("The initial year cannot be greater than the final year")

    def resolve(track_id: Any) -> str:
        if not isinstance(track_id, str) or re.fullmatch(r"[0-9a-f]{64}", track_id) is None or track_id not in paths:
            raise ValueError("Track identity is not in the current authorized library")
        return paths[track_id]

    def resolve_list(field: str) -> list[str]:
        values = params.get(field, [])
        if not isinstance(values, list) or len(values) > 100:
            raise ValueError("Track selections must be lists of at most 100 identities")
        resolved = [resolve(value) for value in values]
        if len(set(resolved)) != len(resolved):
            raise ValueError("Track selections cannot contain duplicates")
        return resolved

    start = resolve(params["startTrackId"]) if "startTrackId" in params else None
    end = resolve(params["endTrackId"]) if "endTrackId" in params else None
    required, excluded = resolve_list("requiredTrackIds"), set(resolve_list("excludedTrackIds"))
    protected = {*required, *([start] if start else []), *([end] if end else [])}
    if (start is not None and start == end) or protected & excluded:
        raise ValueError("Conflicting track selections")
    if len(protected) > params["targetTrackCount"]:
        raise ValueError("The requested track count is smaller than the selected control tracks")
    complete = {track.path for track in records if track.metadata_status == "complete"}
    if not protected <= complete:
        raise ValueError("Selected control tracks need complete metadata before preparation")
    return DJSetIntent(
        name=name,
        strategy=strategy,
        target_track_count=params["targetTrackCount"],
        target_minutes=minutes,
        slot_role=role,
        genre_focus=genre.strip() or None if isinstance(genre, str) else None,
        start_path=start,
        end_path=end,
        required_paths=required,
        excluded_paths=excluded,
        year_min=year_min,
        year_max=year_max,
    )


def generate_plan(
    records: list[TrackRecord],
    intent: DJSetIntent,
    checkpoint: Callable[[str], None],
    *,
    loudness_band: LoudnessBand | None = None,
    spectral_cohesion: float = 0.0,
) -> PrepCopilotPlan:
    """Preserve hard filters, control priorities and the bound colour identity."""
    band = DEFAULT_LOUDNESS_BAND if loudness_band is None else loudness_band
    # S16: the period narrows the library before the interactive candidate cap, so
    # the cap can never spend its slots on tracks outside the epoch the DJ asked
    # for. The plan builder applies the same rule per variant for its other callers.
    records = [record for record in records if period_keeps_track(intent, record)]
    manual = [intent.start_path] if intent.start_path is not None else []
    manual.extend(path for path in intent.required_paths if path not in manual)
    controls = DJControls(
        start_path=intent.start_path,
        end_path=intent.end_path,
        manual_order_paths=manual,
        excluded_paths=intent.excluded_paths,
    )
    limit = pool_size_for_slot(
        slot_minutes=intent.target_minutes or intent.target_track_count * PREP_PLAYED_SECONDS_PER_TRACK / 60,
        played_seconds_per_track=PREP_PLAYED_SECONDS_PER_TRACK,
    )
    anchor = None
    if intent.strategy in COLOR_FILTER_STRATEGIES:
        context = plan_recommendation_candidate_context(
            scanned_records=records,
            controls=controls,
            limit=limit,
            strategy_name=intent.strategy,
            loudness_band=band,
        )
        candidates, anchor = context.records, context.color_anchor_path
    else:
        candidates = plan_recommendation_candidates(
            scanned_records=records,
            controls=controls,
            limit=limit,
            strategy_name=intent.strategy,
            loudness_band=band,
        )
    return build_prep_copilot_plan(
        candidates,
        intent,
        color_anchor_path=anchor,
        loudness_band=band,
        spectral_cohesion=spectral_cohesion,
        checkpoint=checkpoint,
    )


# The engine checkpoints before building each of the three variants and once more to close
# the plan, so its 0–3 of 3 progress is named here rather than in the renderer.
PREP_GENERATE_STAGES: tuple[str, ...] = (
    "Preparando alternativa segura",
    "Preparando alternativa equilibrada",
    "Preparando alternativa aventurera",
)
PREP_GENERATE_FINAL_STAGE = "Finalizando la preparación"


def prep_generate_stage(processed_count: object) -> str | None:
    """Spanish name of the stage the engine is on, for its 0–3 of 3 progress."""
    if type(processed_count) is not int or not 0 <= processed_count <= len(PREP_GENERATE_STAGES):
        return None
    if processed_count < len(PREP_GENERATE_STAGES):
        return PREP_GENERATE_STAGES[processed_count]
    return PREP_GENERATE_FINAL_STAGE
