"""Deterministic mapping of raw genre labels onto canonical genres.

A raw label from any source (Discogs style, MusicBrainz genre/tag, free-text
file tag) is reduced to a case- and punctuation-insensitive key and resolved
against the canonical taxonomy plus a CC0 crosswalk of aliases. Unknown labels
resolve to :data:`UNMAPPED` rather than raising.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from importlib.resources import files

from xfinaudio.genre.taxonomy import load_taxonomy

UNMAPPED = "unmapped"

_DATA_PACKAGE = "xfinaudio.genre.data"
_CROSSWALK_FILE = "crosswalk.json"
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _key(raw: str) -> str:
    """Reduce a raw label to a normalized lookup key (lowercase, alnum words)."""
    return _NON_ALNUM.sub(" ", raw.casefold()).strip()


class GenreNormalizer:
    """Resolve raw genre labels to canonical genres using a prebuilt lookup."""

    def __init__(self, lookup: dict[str, str]) -> None:
        self._lookup = lookup

    @classmethod
    def default(cls) -> GenreNormalizer:
        """Return the shared normalizer built from the taxonomy + crosswalk."""
        return _default_normalizer()

    def normalize(self, raw: str) -> str:
        """Return the canonical genre for ``raw`` or :data:`UNMAPPED`."""
        if not raw:
            return UNMAPPED
        key = _key(raw)
        if not key:
            return UNMAPPED
        return self._lookup.get(key, UNMAPPED)


def _load_crosswalk_aliases() -> dict[str, str]:
    raw = files(_DATA_PACKAGE).joinpath(_CROSSWALK_FILE).read_text(encoding="utf-8")
    payload = json.loads(raw)
    return payload.get("aliases", {})


def _build_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    # Every canonical genre maps to itself via its normalized key.
    for genre in load_taxonomy().genres:
        lookup[_key(genre)] = genre
    # Crosswalk aliases override/extend; alias keys are normalized at load.
    for alias, canonical in _load_crosswalk_aliases().items():
        lookup[_key(alias)] = canonical
    return lookup


@lru_cache(maxsize=1)
def _default_normalizer() -> GenreNormalizer:
    return GenreNormalizer(_build_lookup())
