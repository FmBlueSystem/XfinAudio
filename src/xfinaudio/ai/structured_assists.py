"""Optional language interpretation; local matching/edit engines remain authoritative."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from xfinaudio.ai.nan_client import Transport
from xfinaudio.ai.privacy import redact_paths
from xfinaudio.ai.structured_common import _ERROR, ask_object
from xfinaudio.desktop.library_query import LibraryQuery


class _StrictLibraryQuery(LibraryQuery):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid", allow_inf_nan=False)
    text: str = Field(default="", max_length=300)
    interpretation_note: Literal[""] = ""


class EditorInterpretation(BaseModel):
    """A bounded operation, never executable model text or a model-selected path."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    operation: Literal["shorten_tracks", "shorten_minutes", "rising_energy", "falling_energy"]
    target: int | None = Field(default=None, ge=1, le=1000)

    @model_validator(mode="after")
    def valid_target(self) -> EditorInterpretation:
        if self.operation.startswith("shorten"):
            if self.target is None or (self.operation == "shorten_minutes" and self.target > 600):
                raise ValueError("A bounded shortening target is required")
        elif self.target is not None:
            raise ValueError("Energy ordering cannot include a target")
        return self

    @property
    def command(self) -> str:
        if self.operation == "shorten_tracks":
            return f"shorten to {self.target} tracks"
        if self.operation == "shorten_minutes":
            return f"shorten to {self.target} minutes"
        return "raise energy" if self.operation == "rising_energy" else "lower energy"


def interpret_library_query(
    request: str, genres: list[str], *, transport: Transport | None = None, timeout: float = 30.0
) -> LibraryQuery:
    """Interpret into visible filters; only existing metadata can match them."""
    if len(genres) > 256 or any(len(genre) > 100 for genre in genres):
        raise ValueError("The genre vocabulary is too large for AI. Use the local filters.")
    safe_genres = sorted({redact_paths(genre) for genre in genres if redact_paths(genre) == genre})
    data = ask_object(
        request,
        {"genres": safe_genres},
        'Schema: {"text": string up to 300 characters, "genre": exact supplied genre or null, '
        '"bpm_min": number in (0,400] or null, "bpm_max": number in (0,400] or null, '
        '"key": Camelot 1A..12B or null, "energy_min": integer 1..10 or null, '
        '"energy_max": integer 1..10 or null}. Omit unused fields. Lower bounds cannot exceed upper bounds. '
        "Energy for descriptive moods is an editable filter suggestion, never a measured track value.",
        transport=transport,
        timeout=timeout,
    )
    try:
        query = _StrictLibraryQuery.model_validate(data)
    except ValidationError:
        raise ValueError(_ERROR) from None
    if query.genre is not None and query.genre not in safe_genres:
        raise ValueError(_ERROR)
    if not any(value is not None and value != "" for value in query.model_dump().values()):
        raise ValueError(_ERROR)
    if redact_paths(query.text) != query.text:
        raise ValueError(_ERROR)
    return LibraryQuery.model_validate(
        query.model_dump()
        | {"interpretation_note": "AI-suggested filters. Review before applying; missing metadata stays unknown."}
    )


def interpret_editor_request(
    request: str, *, transport: Transport | None = None, timeout: float = 30.0
) -> EditorInterpretation:
    data = ask_object(
        request,
        {},
        'Schema: {"operation": "shorten_tracks"|"shorten_minutes"|"rising_energy"|"falling_energy", '
        '"target": integer or null}. Shorten requires an explicitly requested positive target, '
        "at most 1000 tracks or 600 minutes. Energy ordering requires null target. "
        'Never infer a target from "make it shorter". No track list is shared.',
        transport=transport,
        timeout=timeout,
    )
    try:
        return EditorInterpretation.model_validate(data)
    except ValidationError:
        raise ValueError(_ERROR) from None
