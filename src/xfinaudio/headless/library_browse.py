"""Offline Library queries and display-only ordering using existing domain rules."""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING, Any

from xfinaudio.application.library_query import LibraryQuery, parse_library_query
from xfinaudio.headless.common import BackendError, _public_track, _text
from xfinaudio.library.duplicate_grouping import duplicate_group_key, duplicate_representative_sort_key
from xfinaudio.library.models import TrackRecord

if TYPE_CHECKING:
    from xfinaudio.headless.backend import HeadlessBackend

BROWSE_FIELDS = {"library.query": {"query", "request", "status", "sortBy", "descending", "hideDuplicates"}}
QUERY_FIELDS = {"text", "genre", "bpm_min", "bpm_max", "key", "energy_min", "energy_max"}
SORT_FIELDS = {
    "title": "title",
    "artist": "artist",
    "genre": "genre",
    "bpm": "bpm",
    "key": "camelot_key",
    "energy": "energy_level",
    "duration": "duration",
    "format": "audio_format",
    "bitrate": "bitrate_kbps",
}


def _sort_value(record: TrackRecord, field: str) -> Any:
    value = getattr(record, field)
    if isinstance(value, str):
        value = value.strip().casefold()
        if not value:
            return None
        if field == "camelot_key":
            match = re.fullmatch(r"(1[0-2]|[1-9])([ab])", value)
            return (0, int(match[1]), match[2]) if match else (1, 0, value)
        if field == "audio_format":
            return (value, (record.audio_codec or "").casefold())
    if isinstance(value, (int, float)) and not math.isfinite(value):
        return None
    return value


def _suppress(records: list[TrackRecord]) -> list[TrackRecord]:
    groups: dict[tuple[str, str], list[TrackRecord]] = {}
    for record in records:
        key = duplicate_group_key(record.title, record.artist, placeholder="—")
        if key is not None:
            groups.setdefault(key, []).append(record)
    hidden: set[str] = set()
    for group in groups.values():
        chosen = min(
            group,
            key=lambda r: duplicate_representative_sort_key(
                is_complete=r.metadata_status == "complete",
                missing_field_count=len(r.missing_required_fields),
                title=r.title or "—",
                path=r.path,
            ),
        )
        hidden.update(r.path for r in group if r.path != chosen.path)
    return [record for record in records if record.path not in hidden]


class LibraryBrowser:
    def __init__(self, backend: HeadlessBackend) -> None:
        self.backend = backend

    def execute(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method not in BROWSE_FIELDS or set(params) - BROWSE_FIELDS[method]:
            raise BackendError("invalid_params", "Unexpected Library filters")
        records = self.backend._records()
        genres = sorted({record.genre for record in records if record.genre}, key=str.casefold)
        if "query" in params and "request" in params:
            raise BackendError("invalid_params", "Interpret a request or edit filters, not both")
        try:
            if "request" in params:
                query = parse_library_query(_text(params["request"], "Library request", 2000), genres)
            else:
                value = params.get("query", {})
                if not isinstance(value, dict) or set(value) - QUERY_FIELDS:
                    raise ValueError
                for field in ("text", "genre", "key"):
                    if (
                        field in value
                        and value[field] is not None
                        and (not isinstance(value[field], str) or len(value[field]) > 200 or "\x00" in value[field])
                    ):
                        raise ValueError
                for field in ("bpm_min", "bpm_max", "energy_min", "energy_max"):
                    if field in value and value[field] is not None and type(value[field]) not in (int, float):
                        raise ValueError
                query = LibraryQuery.model_validate(value)
        except ValueError as exc:
            raise BackendError("invalid_query", "Use valid genre, BPM, key, energy or title/artist filters") from exc
        status, sort_by = params.get("status", "all"), params.get("sortBy", "title")
        descending, hide = params.get("descending", False), params.get("hideDuplicates", False)
        if (
            status not in ("all", "complete", "incomplete")
            or not isinstance(sort_by, str)
            or sort_by not in SORT_FIELDS
        ):
            raise BackendError("invalid_params", "Invalid Library ordering or metadata status")
        if type(descending) is not bool or type(hide) is not bool:
            raise BackendError("invalid_params", "Invalid Library display option")
        # Qt first filters matches, then chooses a representative only among visible rows.
        matches = [r for r in records if query.matches(r) and (status == "all" or r.metadata_status == status)]
        visible = _suppress(matches) if hide else matches
        suppressed = len(matches) - len(visible)
        field = SORT_FIELDS[sort_by]
        known, unknown = [], []
        # Tie order is deterministic and direction independent; no source list is mutated.
        for record in sorted(visible, key=lambda r: r.path):
            (unknown if _sort_value(record, field) is None else known).append(record)
        known.sort(key=lambda r: _sort_value(r, field), reverse=descending)
        return {
            "tracks": [_public_track(r) for r in known + unknown],
            "query": query.model_dump(),
            "genres": genres,
            "totalCount": len(records),
            "matchedCount": len(visible),
            "suppressedCount": suppressed,
        }
