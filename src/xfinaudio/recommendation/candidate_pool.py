"""Pure recommendation candidate-pool policy — no Qt dependencies."""

from __future__ import annotations

from xfinaudio.library.duplicate_grouping import duplicate_representative_sort_key, playlist_duplicate_group_key
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls, preserved_control_paths

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
    parsed_track = _parse_camelot_key(track_key)
    parsed_anchor = _parse_camelot_key(anchor_key)
    if parsed_track is None or parsed_anchor is None:
        return False
    track_num, track_letter = parsed_track
    anchor_num, anchor_letter = parsed_anchor
    direct_delta = abs(track_num - anchor_num)
    circular_delta = min(direct_delta, 12 - direct_delta)
    return (track_letter == anchor_letter and circular_delta <= 1) or (
        track_num == anchor_num and track_letter != anchor_letter
    )


def _parse_camelot_key(key: str) -> tuple[int, str] | None:
    if len(key) < 2:
        return None
    number_text = key[:-1]
    letter = key[-1]
    if letter not in {"A", "B"}:
        return None
    try:
        number = int(number_text)
    except ValueError:
        return None
    if not 1 <= number <= 12:
        return None
    return number, letter


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


def anchor_preflight_warnings(controls: DJControls | None, scanned_records: list[TrackRecord]) -> list[str]:
    """Return user-facing warnings for control anchors that can't be used.

    A start/end/manual track that is missing from the scanned library or is
    incomplete (missing required metadata) cannot anchor a recommendation. Surfacing
    this BEFORE generating explains why the result ignores those tracks, instead of
    leaving the user to guess. Pure and side-effect free.
    """
    if controls is None:
        return []
    by_path = {record.path: record for record in scanned_records}

    def _label(path: str) -> str:
        record = by_path.get(path)
        if record is not None and record.title:
            return record.title
        return path.rsplit("/", 1)[-1]

    def _usable(path: str) -> bool:
        record = by_path.get(path)
        return record is not None and record.metadata_status == "complete"

    warnings: list[str] = []
    for label, path in (("Start", controls.start_path), ("End", controls.end_path)):
        if path is not None and not _usable(path):
            warnings.append(f'{label} track "{_label(path)}" is incomplete or unavailable and will be ignored.')

    incomplete_manual = [path for path in controls.manual_order_paths if not _usable(path)]
    if incomplete_manual:
        warnings.append(
            f"{len(incomplete_manual)} manually-ordered track(s) are incomplete or unavailable and will be ignored."
        )
    return warnings


def dedupe_recommendation_duplicates(
    records: list[TrackRecord], controls: DJControls | None, *, protected_path: str | None = None
) -> list[TrackRecord]:
    """Collapse near-duplicate title+artist versions to one representative each.

    Uses `playlist_duplicate_group_key` (`xfinaudio.library.duplicate_grouping`)
    — STRICTER than the Library screen's display-only duplicate filter's
    grouping key: parenthetical descriptor content is ignored entirely, so
    e.g. "Too Hot (Clean)" and "Too Hot (Single Version)" are the same song
    for candidate-pool purposes (maintainer decision 2026-07-20). The Library
    display filter keeps using the conservative key unchanged. Control tracks
    (locked, manual-order, start, end) are never removed: when a duplicate
    group contains one or more control tracks, all controls in the group
    survive and only non-control siblings are suppressed. Otherwise the
    representative is chosen deterministically via
    `duplicate_representative_sort_key` (complete status first, fewer missing
    fields, shorter title, path as final tiebreak). Order-preserving: the
    result keeps the original relative order of surviving records.

    Only `metadata_status == "complete"` records are grouped/suppressed;
    incomplete records (including incomplete control tracks) pass through
    untouched. `build_recommendation_pool` already drops incomplete records
    entirely (including incomplete controls, which never make it into its
    priority set), so letting an incomplete control "win" a group here would
    silently suppress its complete non-control sibling and then lose the
    song outright downstream — this is the exact defect this restriction
    prevents.
    """
    preserve = preserved_control_paths(controls) if controls is not None else set()
    # A bound same_color_energy anchor is a protected identity: it must survive
    # dedupe intact so a duplicate sibling can never become the representative
    # and silently replace the anchor. It is protected WITHOUT becoming a control
    # (no start_path conversion, no playlist-order change).
    if protected_path is not None:
        preserve = preserve | {protected_path}

    groups: dict[tuple[str, str], list[TrackRecord]] = {}
    for record in records:
        if record.metadata_status != "complete":
            continue
        key = playlist_duplicate_group_key(record.title, record.artist)
        if key is None:
            continue
        groups.setdefault(key, []).append(record)

    suppressed: set[str] = set()
    for group in groups.values():
        if len(group) < 2:
            continue
        controls_in_group = [r for r in group if r.path in preserve]
        if controls_in_group:
            keep_paths = {r.path for r in controls_in_group}
        else:
            representative = min(
                group,
                key=lambda r: duplicate_representative_sort_key(
                    is_complete=r.metadata_status == "complete",
                    missing_field_count=len(r.missing_required_fields),
                    title=r.title or "",
                    path=r.path,
                ),
            )
            keep_paths = {representative.path}
        for record in group:
            if record.path not in keep_paths:
                suppressed.add(record.path)

    return [r for r in records if r.path not in suppressed]


def _interleave_by_energy(tracks: list[TrackRecord], limit: int) -> list[TrackRecord]:
    """Take from each energy level in turn, best-ranked first within each level.

    Similarity ranking alone fills the pool with the anchor's own energy: on a
    real library an E7 anchor produced a 120-track pool that was 80% level 7,
    leaving the arc nothing to shape. Round-robin guarantees the ends of the
    range survive, at the cost of some average transition quality -- a set with
    no dynamics is the worse trade.
    """
    by_level: dict[int, list[TrackRecord]] = {}
    unknown: list[TrackRecord] = []
    for candidate in tracks:
        if candidate.energy_level is None:
            unknown.append(candidate)
        else:
            by_level.setdefault(candidate.energy_level, []).append(candidate)

    interleaved: list[TrackRecord] = []
    queues = [by_level[level] for level in sorted(by_level)]
    position = 0
    while len(interleaved) < limit and any(position < len(queue) for queue in queues):
        for queue in queues:
            if position < len(queue):
                interleaved.append(queue[position])
                if len(interleaved) >= limit:
                    break
        position += 1
    if len(interleaved) < limit:
        interleaved.extend(unknown[: limit - len(interleaved)])
    return interleaved


def build_recommendation_pool(
    scanned_records: list[TrackRecord],
    controls: DJControls | None,
    limit: int = _DEFAULT_LIMIT,
    *,
    spread_energy: bool = False,
    protected_path: str | None = None,
) -> list[TrackRecord]:
    """Return an interactive-size recommendation pool while preserving control tracks at the front.

    ``spread_energy`` fills the remaining slots by taking from each energy level
    in turn rather than purely by similarity, so strategies that trace an arc
    have material at both ends of the range. Off by default: strategies that
    hold one level want the concentrated pool.

    ``protected_path`` is a bound same_color_energy anchor that must survive the
    cap. It is retained WITHOUT being promoted to a control (its playlist-order
    position is unchanged); it simply cannot be trimmed away by the interactive
    cap, so downstream final enforcement can still bind it.
    """
    pool = _build_recommendation_pool(scanned_records, controls, limit, spread_energy=spread_energy)
    if protected_path is None or any(track.path == protected_path for track in pool):
        return pool
    protected = next((track for track in scanned_records if track.path == protected_path), None)
    if protected is None or protected.metadata_status != "complete":
        return pool
    # Keep the anchor by displacing the last trimmable slot, preserving the
    # existing relative order of everything ahead of it.
    return [*pool[: max(0, len(pool) - 1)], protected] if pool else [protected]


def _build_recommendation_pool(
    scanned_records: list[TrackRecord],
    controls: DJControls | None,
    limit: int = _DEFAULT_LIMIT,
    *,
    spread_energy: bool = False,
) -> list[TrackRecord]:
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
        if spread_energy and remaining_slots:
            return [*priority_records, *_interleave_by_energy(remaining_records, remaining_slots)]
        return [*priority_records, *remaining_records[:remaining_slots]]

    anchor_terms = set().union(*(_track_vibe_terms(r) for r in priority_records))
    if not anchor_terms:
        if spread_energy:
            return [*priority_records, *_interleave_by_energy(remaining_records, remaining_slots)]
        return [*priority_records, *remaining_records[:remaining_slots]]

    terms_by_path = {r.path: _track_vibe_terms(r) for r in remaining_records}
    compatible = [r for r in remaining_records if anchor_terms & terms_by_path[r.path]]
    compatible_paths = {r.path for r in compatible}
    fallback = [r for r in remaining_records if r.path not in compatible_paths]
    compatible = sorted(compatible, key=lambda r: _track_similarity_key(anchor_terms, priority_records, r))
    fallback = sorted(fallback, key=lambda r: _track_similarity_key(anchor_terms, priority_records, r))
    if spread_energy:
        ranked = _interleave_by_energy([*compatible, *fallback], remaining_slots)
        return [*priority_records, *ranked][:limit]
    return [*priority_records, *compatible, *fallback][:limit]
