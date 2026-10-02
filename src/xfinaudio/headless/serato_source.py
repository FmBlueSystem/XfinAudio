"""Reload complete export sources and assess the exact order with the real engine."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from xfinaudio.application.playlist_edit_assessment import assess_playlist_edit
from xfinaudio.headless.common import BackendError, _inside, _public_track
from xfinaudio.headless.metadata_export import select_metadata_worklist
from xfinaudio.headless.playlist_editor import _playlist_id, _revision
from xfinaudio.headless.serato_safety import opaque_id, source_identity
from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.dj_readiness import build_dj_readiness_report
from xfinaudio.quality.recommendation_quality import build_quality_report
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation

if TYPE_CHECKING:
    from xfinaudio.headless.backend import HeadlessBackend


@dataclass(frozen=True)
class ExportSource:
    selector: dict[str, Any]
    revision: str
    recommendation: PlaylistRecommendation | None
    tracks: list[dict[str, Any]]
    paths: tuple[Path, ...]
    readiness: str
    warnings: list[str]
    blockers: list[str]
    variant: str | None
    metadata_records: tuple[TrackRecord, ...] | None = None


def load_source(backend: HeadlessBackend, value: Any) -> ExportSource:
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("kind"), str)
        or value["kind"] not in {"saved", "review", "metadata"}
    ):
        raise BackendError("invalid_params", "Choose a saved set, current review or metadata worklist")
    records = {track.path: track for track in backend._records()}
    recommendation = None
    variant = None
    blockers: list[str] = []
    metadata_records = None
    if value["kind"] == "metadata":
        metadata_records = select_metadata_worklist(list(records.values()), value)
        paths = [record.path for record in metadata_records]
        origin_revision = value
    elif value["kind"] == "saved":
        if set(value) != {"kind", "playlistId"}:
            raise BackendError("invalid_params", "Invalid saved export source")
        playlist = backend.playlists.get_by_id(_playlist_id(value["playlistId"]))
        if playlist is None:
            raise BackendError("not_found", "Saved set was not found")
        paths = playlist.track_paths
        origin_revision = _revision(playlist)
    else:
        if set(value) != {"kind", "reviewId"}:
            raise BackendError("invalid_params", "Invalid review export source")
        review_id = opaque_id(value["reviewId"])
        review = backend.review
        if review is None or backend.review_id != review_id:
            raise BackendError("stale_review", "Prepare a current review before exporting")
        try:
            backend.review_actions.verify(review_id)
        except BackendError:
            blockers.append("Review sources or settings changed; generate a new review")
        recommendation = review.recommendation.model_copy(deep=True)
        variant = review.variant_name
        paths = [track.path for track in recommendation.ordered_tracks]
        origin_revision = [review_id, recommendation.model_dump(mode="json"), backend.review_blocked]
        if backend.review_blocked:
            blockers.append("The current review has unresolved blockers")
        if any(records.get(track.path) != track for track in recommendation.ordered_tracks):
            blockers.append("Scanned metadata changed; generate a new review")
    if len(paths) > 500:
        raise BackendError("export_too_large", "Choose at most 500 track references for this export")
    snapshots = []
    tracks = []
    for path in paths:
        record = records.get(path)
        identity = None
        try:
            if not any(_inside(Path(path), root) for root in backend.roots):
                raise OSError("Unauthorized source")
            identity = source_identity(Path(path))
        except (OSError, RuntimeError):
            pass
        missing = record is None or identity is None
        if missing:
            blockers.append("A saved source is missing, changed, or outside the scanned library")
        shown = record or TrackRecord(path=path, title=Path(path).stem)
        tracks.append({**_public_track(shown), "missing": missing})
        snapshots.append([path, record.model_dump(mode="json") if record else None, identity])
    revision = hashlib.sha256(
        json.dumps([origin_revision, snapshots], ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()
    report = None
    if not blockers and metadata_records is None:
        if recommendation is None:
            try:
                assessment = assess_playlist_edit(paths, list(records.values()))
                recommendation, report = assessment.recommendation, assessment.readiness
            except ValueError:
                blockers.append("Repair required metadata or missing transitions before exporting this set")
        else:
            report = build_dj_readiness_report(recommendation, build_quality_report(recommendation))
    warnings = (
        [
            "Lista de trabajo de metadatos: no certifica preparación DJ ni corrige etiquetas. "
            "Revisa los datos en Serato y vuelve a escanear."
        ]
        if metadata_records is not None
        else []
    )
    if report is not None:
        blockers.extend(check.detail for check in report.checks if check.status == "blocked")
        warnings.extend(check.detail for check in report.checks if check.status == "needs_review")
    return ExportSource(
        dict(value),
        revision,
        recommendation,
        tracks,
        tuple(Path(path) for path in paths),
        "blocked"
        if blockers
        else "needs_review"
        if metadata_records is not None
        else report.status
        if report is not None
        else "blocked",
        warnings,
        list(dict.fromkeys(blockers)),
        variant,
        metadata_records,
    )
