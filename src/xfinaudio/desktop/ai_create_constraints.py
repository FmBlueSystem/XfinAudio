"""Merge and validate local hard constraints before showing or accepting AI intent."""

from __future__ import annotations

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.prep_copilot import DJSetIntent
from xfinaudio.recommendation.strategies import available_strategies


def confirmed_intent(intent: DJSetIntent, controls: DJControls | None, tracks: list[TrackRecord]) -> DJSetIntent:
    controls = controls or DJControls()
    required = list(
        dict.fromkeys([*controls.manual_order_paths, *intent.required_paths, *sorted(controls.locked_paths)])
    )
    excluded = set(controls.excluded_paths) | intent.excluded_paths
    start = controls.start_path or intent.start_path
    end = controls.end_path or intent.end_path
    known = {track.path for track in tracks}
    mandatory = set(required) | {path for path in (start, end) if path}
    if not (mandatory | excluded) <= known:
        raise ValueError("A requested track is no longer in the library. Interpret the request again.")
    if mandatory & excluded:
        raise ValueError("A required or boundary track is excluded. Edit the request or local constraints.")
    if len(mandatory) > intent.target_track_count:
        raise ValueError("Track count is smaller than the required tracks. Increase it before confirming.")
    if intent.strategy not in available_strategies():
        raise ValueError("Choose an available ordering strategy.")
    return DJSetIntent.model_validate(
        {
            **intent.model_dump(),
            "required_paths": required,
            "excluded_paths": excluded,
            "start_path": start,
            "end_path": end,
        }
    )
