"""Canonical genre taxonomy loaded from an in-package CC0 JSON asset.

The taxonomy is a flat set of canonical genre names plus a coarse parent
hierarchy (e.g. ``Tech House`` -> ``House``). It carries no source-specific
data and is safe to ship under the project's GPL-3.0 license.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files

from pydantic import BaseModel, ConfigDict

_DATA_PACKAGE = "xfinaudio.genre.data"
_TAXONOMY_FILE = "taxonomy.json"


class Taxonomy(BaseModel):
    """Immutable canonical genre taxonomy.

    ``parents`` maps each canonical genre name to its parent genre, or ``None``
    for a top-level genre.
    """

    model_config = ConfigDict(frozen=True)

    parents: dict[str, str | None]

    @property
    def genres(self) -> frozenset[str]:
        """Return the set of all canonical genre names."""
        return frozenset(self.parents)

    def is_canonical(self, genre: str) -> bool:
        """Return ``True`` when ``genre`` is a known canonical genre name."""
        return genre in self.parents

    def parent_of(self, genre: str) -> str | None:
        """Return the parent of ``genre``, or ``None`` if top-level/unknown."""
        return self.parents.get(genre)


@lru_cache(maxsize=1)
def load_taxonomy() -> Taxonomy:
    """Load and cache the canonical taxonomy from the in-package JSON asset."""
    raw = files(_DATA_PACKAGE).joinpath(_TAXONOMY_FILE).read_text(encoding="utf-8")
    payload = json.loads(raw)
    parents: dict[str, str | None] = {}
    for node in payload["genres"]:
        parents[node["name"]] = node.get("parent")
    return Taxonomy(parents=parents)
