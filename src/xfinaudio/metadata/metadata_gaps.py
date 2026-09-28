"""Deterministic metadata gap report for a scanned library.

Pure domain: takes ``TrackRecord`` objects in and returns a report plus its text
exports. It deliberately introduces **no** new completeness rule -- every gap is
read from the parser's existing required-field contract (the same three fields
``parse_mixedinkey_tags`` records in ``missing_required_fields``), so candidate
pools, playlists, and DJ readiness keep seeing exactly the same tracks as
complete.

``release_year`` is informational only: it is surfaced per entry and counted as
coverage, but it never decides whether a track is a gap.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from collections.abc import Iterable
from io import StringIO

from pydantic import BaseModel, ConfigDict, Field

from xfinaudio.library.models import TrackRecord

# The parser's required fields, in its own order. A field is a gap when its value
# is None, which is precisely what parse_mixedinkey_tags serializes into
# missing_required_fields; reading the values keeps the report independent of the
# persisted JSON list while preserving the exact completeness semantics.
REQUIRED_GAP_FIELDS = ("bpm", "camelot_key", "energy_level")


class MetadataGapCounts(BaseModel):
    """Per-field missing counts across the scanned library."""

    model_config = ConfigDict(frozen=True)

    bpm: int
    camelot_key: int
    energy_level: int


class MetadataGapYearCoverage(BaseModel):
    """Informational release_year coverage. Not a completeness signal."""

    model_config = ConfigDict(frozen=True)

    with_release_year: int
    without_release_year: int


class MetadataGapEntry(BaseModel):
    """One track with at least one required-field gap."""

    model_config = ConfigDict(frozen=True)

    path: str
    title: str | None = None
    artist: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
    release_year: int | None = None


class MetadataGapReport(BaseModel):
    """Deterministic summary of metadata gaps, ordered by path."""

    model_config = ConfigDict(frozen=True)

    total_tracks: int
    complete_count: int
    incomplete_count: int
    gaps: MetadataGapCounts
    year_coverage: MetadataGapYearCoverage
    entries: list[MetadataGapEntry] = Field(default_factory=list)


def build_metadata_gap_report(records: Iterable[TrackRecord]) -> MetadataGapReport:
    """Return a gap report for ``records``, sorted by path and stable in field order."""
    track_list = list(records)
    gap_counts: Counter[str] = Counter()
    entries: list[MetadataGapEntry] = []
    with_release_year = 0

    for record in track_list:
        # The parser's rule, reused: a required field is missing when it is None.
        # Sorted so the per-track list has one explicit, stable order.
        missing_fields = sorted(field_name for field_name in REQUIRED_GAP_FIELDS if getattr(record, field_name) is None)
        for field_name in missing_fields:
            gap_counts[field_name] += 1
        if record.release_year is not None:
            with_release_year += 1
        if missing_fields:
            entries.append(
                MetadataGapEntry(
                    path=record.path,
                    title=record.title,
                    artist=record.artist,
                    missing_fields=missing_fields,
                    release_year=record.release_year,
                )
            )

    entries.sort(key=lambda entry: entry.path)
    return MetadataGapReport(
        total_tracks=len(track_list),
        complete_count=len(track_list) - len(entries),
        incomplete_count=len(entries),
        gaps=MetadataGapCounts(
            bpm=gap_counts["bpm"],
            camelot_key=gap_counts["camelot_key"],
            energy_level=gap_counts["energy_level"],
        ),
        year_coverage=MetadataGapYearCoverage(
            with_release_year=with_release_year,
            without_release_year=len(track_list) - with_release_year,
        ),
        entries=entries,
    )


def export_metadata_gap_report_json(report: MetadataGapReport) -> str:
    """Return a deterministic JSON export for a metadata gap report."""
    return json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def export_metadata_gap_report_csv(report: MetadataGapReport) -> str:
    """Return a CSV export with one row per gapped track and stable columns."""
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["path", "title", "artist", "missing_fields", "release_year"],
        lineterminator="\n",
    )
    writer.writeheader()
    for entry in report.entries:
        writer.writerow(
            {
                "path": entry.path,
                "title": entry.title or "",
                "artist": entry.artist or "",
                "missing_fields": ";".join(entry.missing_fields),
                "release_year": entry.release_year if entry.release_year is not None else "",
            }
        )
    return output.getvalue()


__all__ = [
    "REQUIRED_GAP_FIELDS",
    "MetadataGapCounts",
    "MetadataGapEntry",
    "MetadataGapReport",
    "MetadataGapYearCoverage",
    "build_metadata_gap_report",
    "export_metadata_gap_report_csv",
    "export_metadata_gap_report_json",
]
