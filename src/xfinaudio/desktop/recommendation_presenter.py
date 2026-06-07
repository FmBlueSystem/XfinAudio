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


def _camelot_compatible(track_key: str | None, anchor_key: str | None) -> bool:
    if track_key is None or anchor_key is None:
        return False
    if track_key == anchor_key:
        return True
    track_num = int(track_key[:-1])
    track_letter = track_key[-1]
    anchor_num = int(anchor_key[:-1])
    anchor_letter = anchor_key[-1]
    return (track_letter == anchor_letter and abs(track_num - anchor_num) <= 1) or (
        track_num == anchor_num and track_letter != anchor_letter
    )


def _track_similarity_key(
    anchor_terms: set[str],
    anchor_tracks: list[TrackRecord],
    track: TrackRecord,
) -> tuple[int, int, int, float, float, str]:
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

    if bpm_distance <= 3.0:
        bpm_bucket = 0
    elif bpm_distance <= 6.0:
        bpm_bucket = 1
    else:
        bpm_bucket = 2

    if track.camelot_key is not None and any(
        _camelot_compatible(track.camelot_key, a.camelot_key) for a in anchor_tracks if a.camelot_key is not None
    ):
        key_bucket = 0
    elif track.camelot_key is not None:
        key_bucket = 1
    else:
        key_bucket = 2

    return (bpm_bucket, key_bucket, -overlap_count, float(energy_distance), bpm_distance, track.path)


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
