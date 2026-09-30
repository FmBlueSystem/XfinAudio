"""Anonymous, grounded saved-set retrieval; no playlist or track writes."""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from xfinaudio.ai.nan_client import Transport
from xfinaudio.ai.privacy import redact_paths
from xfinaudio.ai.structured_common import _ERROR, ask_object
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_models import Playlist


class SavedSetDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid", allow_inf_nan=False)
    id: str = Field(pattern=r"^s\d{1,6}$")
    track_count: int = Field(ge=0, le=1_000_000)
    genres: tuple[str, ...]
    duration_minutes: float | None
    duration_known: int = Field(ge=0)
    bpm_min: float | None
    bpm_max: float | None
    bpm_known: int = Field(ge=0)
    energy_min: int | None
    energy_max: int | None
    energy_known: int = Field(ge=0)


class SavedInterpretation(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    action: Literal["find", "compare"]
    selected_ids: tuple[str, ...] = Field(max_length=200)

    @field_validator("selected_ids", mode="before")
    @classmethod
    def json_array(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value


def build_saved_descriptors(
    playlists: Sequence[Playlist], records: Sequence[TrackRecord]
) -> tuple[SavedSetDescriptor, ...]:
    """Generate ephemeral index IDs and finite aggregate facts, never raw metadata."""
    if len(playlists) > 200:
        raise ValueError("Choose at most 200 saved sets for AI retrieval.")
    by_path = {record.path: record for record in records}
    paths = tuple(by_path)
    result = []
    for index, playlist in enumerate(playlists):
        tracks = [by_path[path] for path in playlist.track_paths if path in by_path]
        durations = [r.duration for r in tracks if r.duration is not None and _positive(r.duration)]
        bpms = [r.bpm for r in tracks if _positive(r.bpm) and r.bpm is not None and r.bpm <= 400]
        energies = [r.energy_level for r in tracks if r.energy_level is not None and 1 <= r.energy_level <= 10]
        genres = sorted(
            {r.genre for r in tracks if r.genre and len(r.genre) <= 100 and redact_paths(r.genre, paths) == r.genre}
        )
        if len(genres) > 64:
            raise ValueError("Too many genres in one saved set for AI retrieval.")
        result.append(
            SavedSetDescriptor(
                id=f"s{index}",
                track_count=len(playlist.track_paths),
                genres=tuple(genres),
                duration_minutes=sum(d for d in durations if d is not None) / 60
                if tracks and len(durations) == len(playlist.track_paths)
                else None,
                duration_known=len(durations),
                bpm_min=min(bpms) if bpms else None,
                bpm_max=max(bpms) if bpms else None,
                bpm_known=len(bpms),
                energy_min=min(energies) if energies else None,
                energy_max=max(energies) if energies else None,
                energy_known=len(energies),
            )
        )
    return tuple(result)


def anonymize_saved_request(request: str, playlists: Sequence[Playlist]) -> str:
    """Map named references locally in one pass; duplicate names need clarification."""
    lookup: dict[str, str] = {}
    duplicates: set[str] = set()
    for index, playlist in enumerate(playlists):
        name = playlist.name.strip().casefold()
        if name in lookup:
            duplicates.add(name)
        elif name:
            lookup[name] = f"s{index}"
    pattern = re.compile(
        r"(?<!\w)(?:" + "|".join(re.escape(name) for name in sorted(lookup, key=len, reverse=True)) + r")(?!\w)",
        re.IGNORECASE,
    )

    def replace(match: re.Match[str]) -> str:
        name = match[0].casefold()
        if name in duplicates:
            raise ValueError("Several saved sets have the same name. Rename them or select them manually.")
        return lookup[name]

    text = pattern.sub(replace, request) if lookup else request
    return redact_paths(text, (path for playlist in playlists for path in playlist.track_paths))


def interpret_saved_request(
    request: str,
    descriptors: Sequence[SavedSetDescriptor],
    *,
    transport: Transport | None = None,
    timeout: float = 30.0,
) -> SavedInterpretation:
    if not descriptors or len(descriptors) > 200:
        raise ValueError("Choose between 1 and 200 saved sets for AI retrieval.")
    known = {descriptor.id for descriptor in descriptors}
    if len(known) != len(descriptors):
        raise ValueError("Saved set references must be unique.")
    # Validate even caller-supplied descriptors and sanitize each outgoing string
    # before JSON serialization. Never accept a raw playlist/record dictionary.
    context = []
    for descriptor in descriptors:
        validated = SavedSetDescriptor.model_validate(descriptor.model_dump())
        if any(len(g) > 100 or redact_paths(g) != g for g in validated.genres):
            raise ValueError("Saved set genres contain private or unsupported values.")
        context.append(validated.model_dump(mode="json"))
    data = ask_object(
        request,
        context,
        'Schema: {"action":"find"|"compare", "selected_ids":[supplied temporary IDs]}. '
        "Return unique IDs only. Compare needs at least two. Find may return an empty list. "
        "Select from the supplied actual aggregates only; unknown values cannot satisfy numeric constraints. "
        "Do not generate comparisons: the local application computes them.",
        transport=transport,
        timeout=timeout,
    )
    try:
        result = SavedInterpretation.model_validate(data)
    except ValidationError:
        raise ValueError(_ERROR) from None
    ids = result.selected_ids
    if set(ids) - known or len(set(ids)) != len(ids) or (result.action == "compare" and len(ids) < 2):
        raise ValueError(_ERROR)
    return result


def _positive(value: float | None) -> bool:
    return value is not None and math.isfinite(value) and value > 0
