"""Pure filtering functions for the track library — no Qt dependencies."""

from __future__ import annotations

from xfinaudio.library.models import TrackRecord


def metadata_status_records(records: list[TrackRecord], status: str) -> list[TrackRecord]:
    """Return records matching the requested metadata status."""
    return [r for r in records if r.metadata_status == status]


def metadata_missing_field_records(records: list[TrackRecord], missing_field: str) -> list[TrackRecord]:
    """Return incomplete records missing the requested metadata field."""
    return [r for r in records if r.metadata_status == "incomplete" and missing_field in r.missing_required_fields]
