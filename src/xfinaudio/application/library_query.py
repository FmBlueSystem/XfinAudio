"""Validated, offline Library query interpretation. Never infers missing metadata."""

from __future__ import annotations

import math
import re
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, model_validator

from xfinaudio.library.models import TrackRecord


class LibraryQuery(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    interpretation_note: str = ""
    text: str = ""
    genre: str | None = None
    bpm_min: float | None = Field(default=None, gt=0, le=400)
    bpm_max: float | None = Field(default=None, gt=0, le=400)
    key: str | None = Field(default=None, pattern=r"^(?:[1-9]|1[0-2])[AB]$")
    energy_min: int | None = Field(default=None, ge=1, le=10)
    energy_max: int | None = Field(default=None, ge=1, le=10)

    @model_validator(mode="after")
    def ordered_ranges(self) -> LibraryQuery:
        for label, low, high in (("BPM", self.bpm_min, self.bpm_max), ("Energy", self.energy_min, self.energy_max)):
            if low is not None and high is not None and low > high:
                raise ValueError(f"{label} minimum must not exceed maximum")
        return self

    def matches(self, track: TrackRecord) -> bool:
        if self.text and not any(_plain(self.text) in _plain(value or "") for value in (track.title, track.artist)):
            return False
        if self.genre and self.genre.casefold() != (track.genre or "").casefold():
            return False
        if self.key and self.key != (track.camelot_key or "").upper():
            return False
        for value, low, high in (
            (track.bpm, self.bpm_min, self.bpm_max),
            (track.energy_level, self.energy_min, self.energy_max),
        ):
            if low is None and high is None:
                continue
            if (
                value is None
                or not math.isfinite(value)
                or value <= 0
                or (low is not None and value < low)
                or (high is not None and value > high)
            ):
                return False
        return True


def _plain(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c))


def parse_library_query(request: str, genres: list[str]) -> LibraryQuery:
    """Parse explicit English/Spanish constraints; unsupported words fail visibly.

    Gentle/opening phrases suggest an explicitly labeled, editable 2-5 energy
    range. Residual instructions are rejected rather than silently discarded.
    Quoted title/artist text remains local; missing metadata is never filled.
    """
    remaining = _plain(request.strip())
    values: dict[str, object] = {}
    title = re.search(r'(?:title|artist|titulo|artista)\s+["\']([^"\']+)["\']', remaining)
    if title:
        values["text"] = title[1]
        remaining = remaining[: title.start()] + " " + remaining[title.end() :]
    for genre in sorted(set(genres), key=len, reverse=True):
        pattern = r"(?<!\w)" + re.escape(_plain(genre)) + r"(?!\w)"
        if re.search(pattern, remaining):
            if "genre" in values:
                raise ValueError("Choose one genre, or edit the filters manually")
            values["genre"] = genre
            remaining = re.sub(pattern, " ", remaining)
    number_range = r"(\d+(?:\.\d+)?)(?:\s*(?:-|to|a|y|and)\s*(\d+(?:\.\d+)?))?"
    for label, aliases in (("bpm", "bpm"), ("energy", "energy|energia")):
        patterns = (rf"(?:{aliases})\s*(?:between|entre|:)?\s*{number_range}", rf"{number_range}\s*(?:{aliases})")
        for pattern in patterns:
            match = re.search(pattern, remaining)
            if match:
                values[f"{label}_min"] = float(match[1])
                values[f"{label}_max"] = float(match[2] or match[1])
                remaining = remaining[: match.start()] + " " + remaining[match.end() :]
                break
    key = re.search(r"(?:key|clave|tonalidad)\s*:?\s*(\d+\s*[ab])\b", remaining)
    if key:
        values["key"] = key[1].replace(" ", "").upper()
        remaining = remaining[: key.start()] + " " + remaining[key.end() :]
    gentle = r"\b(?:suave|para abrir|de apertura|warm[ -]?up|gentle|opening)\b"
    if re.search(gentle, remaining):
        remaining = re.sub(gentle, " ", remaining)
        if "energy_min" not in values:
            values.update(
                energy_min=2,
                energy_max=5,
                interpretation_note="Suggested gentle/opening filter: energy 2-5. Edit it to suit your set.",
            )
    remaining = re.sub(
        r"\b(find|show|search|tracks|songs|with|and|between|busca|buscar|muestra|canciones|temas|con|y|entre|de|en|genre|genero)\b",
        " ",
        remaining,
    )
    remaining = re.sub(r"[\s,;:.]+", "", remaining)
    if remaining or not values:
        raise ValueError('Use genre, BPM 120-128, key 8A, energy 4-7, or title "name"; edit unsupported requests')
    return LibraryQuery.model_validate(values)
