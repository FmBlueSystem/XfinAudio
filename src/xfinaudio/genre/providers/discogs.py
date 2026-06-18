"""Discogs genre provider sourced from the CC0 monthly dump.

The provider performs no network I/O. The dump is parsed once via streaming
``ElementTree.iterparse``; raw style labels are resolved to canonical genres
at ingest time and stored in a per-user SQLite cache. ``fetch`` looks up
candidates by normalized (artist, title) and computes confidence from the
agreement of styles across matching releases.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from xml.etree import ElementTree as ET

from xfinaudio.genre.models import GenreCandidate
from xfinaudio.genre.normalizer import UNMAPPED, GenreNormalizer

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS discogs_release_style (
    artist_norm      TEXT NOT NULL,
    title_norm       TEXT NOT NULL,
    canonical_style  TEXT NOT NULL,
    PRIMARY KEY (artist_norm, title_norm, canonical_style)
)
"""
_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS ix_discogs_lookup
    ON discogs_release_style(artist_norm, title_norm)
"""

_LOOKUP_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _lookup_key(value: str) -> str:
    """Return a case- and punctuation-insensitive lookup key."""
    return _LOOKUP_NON_ALNUM.sub(" ", value.casefold()).strip()


def _iter_releases(xml_path: Path) -> Iterable[tuple[str, str, list[str]]]:
    """Yield ``(artist, title, [style, ...])`` for each release in the dump.

    Releases without a resolvable artist, title, or any ``<style>`` children
    are skipped. ``iterparse`` keeps memory bounded by releasing elements as
    they are consumed.
    """
    context = ET.iterparse(xml_path, events=("end",))
    for _event, elem in context:
        if elem.tag != "release":
            continue
        artist_el = elem.find("artists/artist/name")
        title_el = elem.find("title")
        styles = [s.text.strip() for s in elem.findall("styles/style") if s.text]
        if artist_el is not None and artist_el.text and title_el is not None and title_el.text and styles:
            yield (artist_el.text.strip(), title_el.text.strip(), styles)
        elem.clear()


def ingest_discogs_dump(xml_path: Path, cache_path: Path) -> int:
    """Stream-parse a Discogs dump and populate the per-user cache.

    Returns the total number of canonical style rows present in the cache
    after the run, so callers can verify the cache is populated and so the
    function is idempotent across repeated ingests of the same dump.
    """
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    normalizer = GenreNormalizer.default()

    with sqlite3.connect(cache_path) as conn:
        conn.execute(_CREATE_TABLE)
        conn.execute(_CREATE_INDEX)
        for artist, title, styles in _iter_releases(xml_path):
            artist_key = _lookup_key(artist)
            title_key = _lookup_key(title)
            for raw_style in styles:
                canonical = normalizer.normalize(raw_style)
                if canonical == UNMAPPED:
                    continue
                conn.execute(
                    "INSERT OR IGNORE INTO discogs_release_style "
                    "(artist_norm, title_norm, canonical_style) VALUES (?, ?, ?)",
                    (artist_key, title_key, canonical),
                )
        conn.commit()
        (count,) = conn.execute("SELECT COUNT(*) FROM discogs_release_style").fetchone()
    return count


class DiscogsProvider:
    """Offline genre provider backed by the ingested Discogs cache."""

    name = "discogs"

    def __init__(self, cache_path: Path) -> None:
        self._cache_path = cache_path

    def fetch(self, track: object) -> list[GenreCandidate]:
        artist = getattr(track, "artist", None) or ""
        title = getattr(track, "title", None) or ""
        artist_key = _lookup_key(artist)
        title_key = _lookup_key(title)
        if not artist_key or not title_key:
            return []

        with sqlite3.connect(self._cache_path) as conn:
            rows = list(
                conn.execute(
                    "SELECT canonical_style, COUNT(*) "
                    "FROM discogs_release_style "
                    "WHERE artist_norm = ? AND title_norm = ? "
                    "GROUP BY canonical_style",
                    (artist_key, title_key),
                )
            )
        if not rows:
            return []

        total = sum(count for _style, count in rows)
        candidates: list[GenreCandidate] = []
        for canonical, count in rows:
            confidence = (count / total) if total else 0.0
            candidates.append(
                GenreCandidate(
                    canonical_genre=canonical,
                    raw_label=canonical,
                    source="discogs",
                    confidence=confidence,
                )
            )
        return candidates


__all__ = ["DiscogsProvider", "ingest_discogs_dump"]
