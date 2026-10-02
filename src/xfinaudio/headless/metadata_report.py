"""Read-only projection of domain metadata gaps for the Qt-free desktop bridge."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from typing import Any

from xfinaudio.library.models import TrackRecord
from xfinaudio.metadata.metadata_gaps import build_metadata_gap_report
from xfinaudio.metadata.repair_guidance_core import explain_track_gaps, prioritize_repairs, repair_plan_text


def build_metadata_report(
    records: Iterable[TrackRecord], *, locked_paths: frozenset[str] = frozenset()
) -> dict[str, Any]:
    """Expose existing gaps and repair guidance without exporting private path fields."""
    source = list(records)
    report = build_metadata_gap_report(source)
    records_by_path = {record.path: record for record in source}
    priorities = {
        item.path: (rank, item) for rank, item in enumerate(prioritize_repairs(source, locked_paths=locked_paths), 1)
    }
    tracks = []
    for entry in report.entries:
        rank, item = priorities[entry.path]
        tracks.append(
            {
                "id": hashlib.sha256(entry.path.encode("utf-8")).hexdigest(),
                "title": item.title,
                "artist": entry.artist or "",
                "releaseYear": entry.release_year,
                "missingFields": list(entry.missing_fields),
                "explanation": explain_track_gaps(records_by_path[entry.path]),
                "locked": item.locked,
                "priority": rank,
            }
        )
    return {
        "totalTracks": report.total_tracks,
        "completeCount": report.complete_count,
        "incompleteCount": report.incomplete_count,
        "gaps": report.gaps.model_dump(),
        "yearCoverage": {
            "withReleaseYear": report.year_coverage.with_release_year,
            "withoutReleaseYear": report.year_coverage.without_release_year,
        },
        "tracks": tracks,
        "repairPlan": repair_plan_text(source, locked_paths=locked_paths),
        "readOnly": True,
    }
