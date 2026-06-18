"""Mixed In Key metadata parser contract."""

from __future__ import annotations

import base64
import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

CAMELot_RE = re.compile(r"^(?:1[0-2]|[1-9])[AB]$")
ENERGY_TEXT_RE = re.compile(r"Energy\s+([1-9]|10)\b", re.IGNORECASE)
COMMENT_ENERGY_RE = re.compile(r"⚡️?\s*([1-9]|10)")
TAG_FIELDS = ("genre", "mood", "subgenre", "dj_zone", "genre_category")

# Mixed In Key frequently writes the key as a standard musical name (e.g. "Cm", "Bbm", "G")
# instead of Camelot notation. Map every pitch-class (with enharmonic equivalents) to its Camelot
# code: minor keys take the "A" column, major keys take the "B" column (Camelot wheel layout).
_PITCH_TO_CAMELOT_NUMBER = {
    # minor → A column
    ("A", True): 8,
    ("A#", True): 3,
    ("BB", True): 3,
    ("B", True): 10,
    ("C", True): 5,
    ("C#", True): 12,
    ("DB", True): 12,
    ("D", True): 7,
    ("D#", True): 2,
    ("EB", True): 2,
    ("E", True): 9,
    ("F", True): 4,
    ("F#", True): 11,
    ("GB", True): 11,
    ("G", True): 6,
    ("G#", True): 1,
    ("AB", True): 1,
    # major → B column
    ("A", False): 11,
    ("A#", False): 6,
    ("BB", False): 6,
    ("B", False): 1,
    ("C", False): 8,
    ("C#", False): 3,
    ("DB", False): 3,
    ("D", False): 10,
    ("D#", False): 5,
    ("EB", False): 5,
    ("E", False): 12,
    ("F", False): 7,
    ("F#", False): 2,
    ("GB", False): 2,
    ("G", False): 9,
    ("G#", False): 4,
    ("AB", False): 4,
}
_MUSICAL_KEY_RE = re.compile(r"^([A-G])([#b♯♭]?)\s*(m|min|minor|maj|major)?$", re.IGNORECASE)


class MixedInKeyMetadata(BaseModel):
    """Normalized metadata fields discovered from Mixed In Key tags."""

    model_config = ConfigDict(frozen=True)

    title: str | None = None
    artist: str | None = None
    bpm: float | None = None
    camelot_key: str | None = None
    energy_level: int | None = None
    genre: str | None = None
    tags: list[str] = Field(default_factory=list)
    source_fields: dict[str, str] = Field(default_factory=dict)
    missing_required_fields: list[str] = Field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """Return whether BPM, Camelot key, and energy were all parsed."""
        return not self.missing_required_fields


def parse_mixedinkey_tags(raw_tags: dict[str, Any]) -> MixedInKeyMetadata:
    """Parse representative mutagen tag dictionaries into the HELP-3 contract model."""
    tags = _casefold_mapping(raw_tags)
    source_fields: dict[str, str] = {}

    title = _first_text(tags, "title", "tit2")
    if title is not None:
        source_fields["title"] = _source_key(tags, "title", "tit2")

    artist = _first_text(tags, "artist", "tpe1")
    if artist is not None:
        source_fields["artist"] = _source_key(tags, "artist", "tpe1")

    genre = _first_text(tags, "genre", "tcon")
    if genre is not None:
        source_fields["genre"] = _source_key(tags, "genre", "tcon")

    bpm, bpm_source = _parse_bpm(tags)
    if bpm is not None and bpm_source is not None:
        source_fields["bpm"] = bpm_source

    camelot_key, key_source = _parse_camelot_key(tags, title)
    if camelot_key is not None and key_source is not None:
        source_fields["camelot_key"] = key_source

    energy_level, energy_source = _parse_energy(tags, title)
    if energy_level is not None and energy_source is not None:
        source_fields["energy_level"] = energy_source

    normalized_tags = _parse_tags(tags)
    missing_required_fields = [
        field_name
        for field_name, value in (("bpm", bpm), ("camelot_key", camelot_key), ("energy_level", energy_level))
        if value is None
    ]

    return MixedInKeyMetadata(
        title=title,
        artist=artist,
        bpm=bpm,
        camelot_key=camelot_key,
        energy_level=energy_level,
        genre=genre,
        tags=normalized_tags,
        source_fields=source_fields,
        missing_required_fields=missing_required_fields,
    )


def _casefold_mapping(raw_tags: dict[str, Any]) -> dict[str, tuple[str, Any]]:
    return {key.casefold(): (key, value) for key, value in raw_tags.items()}


def _source_key(tags: dict[str, tuple[str, Any]], *candidates: str) -> str:
    for candidate in candidates:
        match = tags.get(candidate.casefold())
        if match is not None:
            return match[0]
    return candidates[0]


def _first_text(tags: dict[str, tuple[str, Any]], *candidates: str) -> str | None:
    for candidate in candidates:
        match = tags.get(candidate.casefold())
        if match is None:
            continue
        values = match[1]
        value = (values[0] if values else None) if isinstance(values, list | tuple) else values
        if value is not None:
            text = str(value).strip()
            if text:
                return text
    return None


def _parse_bpm(tags: dict[str, tuple[str, Any]]) -> tuple[float | None, str | None]:
    for field_name in ("bpm", "tbpm", "ibpm"):
        value = _first_text(tags, field_name)
        if value is None:
            continue
        try:
            return round(float(value), 2), _source_key(tags, field_name)
        except ValueError:
            continue
    return None, None


def _parse_camelot_key(tags: dict[str, tuple[str, Any]], title: str | None) -> tuple[str | None, str | None]:
    encoded = _decode_json_tag(_first_text(tags, "key"))
    if encoded is not None and str(encoded.get("source", "")).casefold() == "mixedinkey":
        candidate = _normalize_camelot(encoded.get("key"))
        if candidate is not None:
            return candidate, "key"

    for field_name in ("initialkey", "tkey"):
        candidate = _normalize_camelot(_first_text(tags, field_name))
        if candidate is not None:
            return candidate, _source_key(tags, field_name)

    candidate = _find_camelot_in_text(title)
    if candidate is not None:
        return candidate, "title"
    return None, None


def _parse_energy(tags: dict[str, tuple[str, Any]], title: str | None) -> tuple[int | None, str | None]:
    encoded = _decode_json_tag(_first_text(tags, "energy"))
    if encoded is not None and str(encoded.get("source", "")).casefold() == "mixedinkey":
        candidate = _normalize_energy(encoded.get("energyLevel"))
        if candidate is not None:
            return candidate, "energy"

    for field_name in ("energylevel", "grouping"):
        candidate = _normalize_energy(_first_text(tags, field_name))
        if candidate is not None:
            return candidate, _source_key(tags, field_name)

    for field_name in ("publisher", "comment"):
        text = _first_text(tags, field_name)
        if text is None:
            continue
        match = ENERGY_TEXT_RE.search(text) or COMMENT_ENERGY_RE.search(text)
        if match is not None:
            return int(match.group(1)), _source_key(tags, field_name)

    if title is not None:
        match = ENERGY_TEXT_RE.search(title)
        if match is not None:
            return int(match.group(1)), "title"
    return None, None


def _parse_tags(tags: dict[str, tuple[str, Any]]) -> list[str]:
    parsed: list[str] = []
    for field_name in TAG_FIELDS:
        value = _first_text(tags, field_name)
        if value is None:
            continue
        for part in value.split(","):
            tag = part.strip()
            if tag and tag not in parsed:
                parsed.append(tag)
    return parsed


def _decode_json_tag(value: str | None) -> dict[str, Any] | None:
    if value is None:
        return None
    compact = "".join(value.split())
    try:
        decoded = base64.b64decode(compact).decode("utf-8")
        parsed = json.loads(decoded)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _normalize_camelot(value: Any) -> str | None:
    if value is None:
        return None
    candidate = str(value).strip().upper()
    if CAMELot_RE.match(candidate):
        return candidate
    return _musical_key_to_camelot(value)


def _musical_key_to_camelot(value: Any) -> str | None:
    """Convert a standard musical key name (e.g. 'Cm', 'Bbm', 'G', 'F#') to Camelot notation.

    Minor keys map to the Camelot "A" column, major keys to the "B" column. Unicode sharp/flat
    glyphs are accepted; a missing mode defaults to major (matching common tag conventions).
    """
    if value is None:
        return None
    text = str(value).strip().replace("♯", "#").replace("♭", "b")
    match = _MUSICAL_KEY_RE.match(text)
    if match is None:
        return None
    letter, accidental, mode = match.group(1).upper(), match.group(2), match.group(3)
    pitch = letter + ("#" if accidental == "#" else "B" if accidental.lower() == "b" else "")
    is_minor = bool(mode) and mode.casefold().startswith("min") or mode == "m"
    number = _PITCH_TO_CAMELOT_NUMBER.get((pitch, is_minor))
    if number is None:
        return None
    return f"{number}{'A' if is_minor else 'B'}"


def _find_camelot_in_text(value: str | None) -> str | None:
    if value is None:
        return None
    match = re.search(r"\b((?:1[0-2]|[1-9])[AB])\b", value, flags=re.IGNORECASE)
    return match.group(1).upper() if match else None


def _normalize_energy(value: Any) -> int | None:
    if value is None:
        return None
    try:
        energy = int(str(value).strip())
    except ValueError:
        return None
    return energy if 1 <= energy <= 10 else None
