"""Pure recommendation pool selection — no Qt dependencies."""

from __future__ import annotations

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls

_DEFAULT_LIMIT = 25


def _track_vibe_terms(track: TrackRecord) -> set[str]:
    values = [*track.tags]
    if track.genre:
        values.extend(track.genre.split(","))
        values.append(track.genre)
    return {v.strip().casefold() for v in values if v.strip()}


def _track_similarity_key(
    anchor_terms: set[str],
    anchor_tracks: list[TrackRecord],
    track: TrackRecord,
) -> tuple[int, float, float, str]:
    terms = _track_vibe_terms(track)
    overlap_count = len(anchor_terms & terms)
    bpm_distance = min(
        (abs((track.bpm or 0.0) - (a.bpm or 0.0)) for a in anchor_tracks if a.bpm is not None),
        default=9999.0,
    )
    energy_distance = min(
        (abs((track.energy_level or 0) - (a.energy_level or 0)) for a in anchor_tracks if a.energy_level is not None),
        default=9999,
    )
    return (-overlap_count, bpm_distance, float(energy_distance), track.path)


def build_recommendation_pool(
    scanned_records: list[TrackRecord],
    controls: DJControls | None,
    limit: int = _DEFAULT_LIMIT,
) -> list[TrackRecord]:
    """Return an interactive-size recommendation pool while preserving control tracks at the front."""
    complete_records = [r for r in scanned_records if r.metadata_status == "complete"]

    priority_paths: list[str] = []
    if controls is not None:
        priority_paths.extend(controls.manual_order_paths)
        if controls.start_path is not None:
            priority_paths.append(controls.start_path)
        if controls.end_path is not None:
            priority_paths.append(controls.end_path)
        priority_paths.extend(sorted(controls.locked_paths))

    unique_priority_paths = list(dict.fromkeys(priority_paths))
    by_path = {r.path: r for r in complete_records}
    priority_records = [by_path[p] for p in unique_priority_paths if p in by_path]
    priority_set = {r.path for r in priority_records}
    remaining_slots = max(0, limit - len(priority_records))
    remaining_records = [r for r in complete_records if r.path not in priority_set]

    if not priority_records or remaining_slots == 0:
        return [*priority_records, *remaining_records[:remaining_slots]]

    anchor_terms = set().union(*(_track_vibe_terms(r) for r in priority_records))
    if not anchor_terms:
        return [*priority_records, *remaining_records[:remaining_slots]]

    terms_by_path = {r.path: _track_vibe_terms(r) for r in remaining_records}
    compatible = [r for r in remaining_records if anchor_terms & terms_by_path[r.path]]
    compatible_paths = {r.path for r in compatible}
    fallback = [r for r in remaining_records if r.path not in compatible_paths]
    compatible = sorted(compatible, key=lambda r: _track_similarity_key(anchor_terms, priority_records, r))
    fallback = sorted(fallback, key=lambda r: _track_similarity_key(anchor_terms, priority_records, r))
    return [*priority_records, *compatible, *fallback][:limit]
