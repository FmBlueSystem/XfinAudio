"""Resolve explicit metadata worklists without granting paths or audio-write authority."""

from __future__ import annotations

from typing import Any

from xfinaudio.headless.common import BackendError, _public_track
from xfinaudio.library.models import TrackRecord

FIELDS = frozenset({"bpm", "camelot_key", "energy_level"})


def select_metadata_worklist(records: list[TrackRecord], value: dict[str, Any]) -> tuple[TrackRecord, ...]:
    """Bind only selected current records matching the original metadata filter."""
    if set(value) != {"kind", "status", "missingField", "trackIds"}:
        raise BackendError("invalid_params", "Choose an exact metadata worklist")
    status, field, selected = value["status"], value["missingField"], value["trackIds"]
    if (
        not isinstance(status, str)
        or status not in {"complete", "incomplete"}
        or (field is not None and (not isinstance(field, str) or field not in FIELDS))
        or (field is not None and status != "incomplete")
        or not isinstance(selected, list)
        or not 1 <= len(selected) <= 500
        or any(not isinstance(item, str) or len(item) != 64 for item in selected)
        or len(set(selected)) != len(selected)
    ):
        raise BackendError("invalid_params", "Choose between one and 500 matching metadata tracks")
    known = {str(_public_track(record)["id"]): record for record in records}
    result = []
    for identity in selected:
        record = known.get(identity)
        if (
            record is None
            or record.metadata_status != status
            or (field is not None and field not in record.missing_required_fields)
        ):
            raise BackendError("stale_source", "The selected metadata worklist changed; refresh it")
        result.append(record)
    return tuple(result)
