"""Last.fm genre provider (runtime, user-keyed).

Uses the optional ``pylast`` library behind a per-user API key. Returns
top tags (folksonomy) for a track, denoised via the shared stoplist and
resolved to the canonical taxonomy. All responses stay in the per-user
SQLite cache; provider data never ships in repo assets.

The provider is import-guarded: missing ``pylast`` is fine, the provider
just becomes a no-op. A test-injectable ``fetcher`` callable lets unit
tests avoid the network entirely.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from collections.abc import Callable
from pathlib import Path

from xfinaudio.genre.models import GenreCandidate
from xfinaudio.genre.normalizer import UNMAPPED, GenreNormalizer

_LOOKUP_NON_ALNUM = re.compile(r"[^a-z0-9]+")
DEFAULT_MIN_INTERVAL_SEC = 1.0

# Reuse the MB folksonomy denoise list (lastfm is also folksonomy).
_TAG_STOPLIST: frozenset[str] = frozenset(
    {
        "seen live",
        "favorites",
        "favorite",
        "favourites",
        "favourite",
        "00s",
        "10s",
        "20s",
        "60s",
        "70s",
        "80s",
        "90s",
        "2000s",
        "2010s",
        "2020s",
        "british",
        "american",
        "english",
        "german",
        "japanese",
        "french",
        "italian",
        "male",
        "female",
        "vocal",
        "instrumental",
        "acoustic",
        "live",
    }
)

# A fetcher returns ``(tag_name, count)`` tuples (counts 0..100) or raises
# on transient failure. Injectable for tests.
LastfmFetcher = Callable[[str, str], list[tuple[str, int]]]


def _lookup_key(value: str) -> str:
    return _LOOKUP_NON_ALNUM.sub(" ", value.casefold()).strip()


class LastfmProvider:
    """Genre provider backed by the Last.fm ``track.getTopTags`` API."""

    name = "lastfm"

    def __init__(
        self,
        *,
        api_key: str = "",
        fetcher: LastfmFetcher | None = None,
        cache_path: Path | None = None,
    ) -> None:
        self._api_key = api_key
        self._fetcher = fetcher
        self._cache_path = cache_path
        self._normalizer = GenreNormalizer.default()

    def fetch(self, track: object) -> list[GenreCandidate]:
        artist = getattr(track, "artist", None) or ""
        title = getattr(track, "title", None) or ""
        artist_key = _lookup_key(artist)
        title_key = _lookup_key(title)
        if not artist_key or not title_key:
            return []

        # Need either an API key or an injected fetcher.
        if not self._api_key and self._fetcher is None:
            return []

        tags = self._lookup(artist_key, title_key, raw_artist=artist, raw_title=title)
        return self._candidates_from_tags(tags)

    # -- internals --------------------------------------------------------

    def _lookup(
        self,
        artist_key: str,
        title_key: str,
        *,
        raw_artist: str,
        raw_title: str,
    ) -> list[tuple[str, int]]:
        if self._cache_path is not None:
            cached = self._cache_get(artist_key, title_key)
            if cached is not None:
                return cached

        tags = self._call_fetcher(raw_artist, raw_title)
        if self._cache_path is not None:
            self._cache_put(artist_key, title_key, tags)
        return tags

    def _call_fetcher(self, artist: str, title: str) -> list[tuple[str, int]]:
        if self._fetcher is not None:
            try:
                return list(self._fetcher(artist, title))
            except Exception:
                return []
        # Live Last.fm fetch via pylast (import-guarded).
        try:
            import pylast  # type: ignore[import-not-found]
        except ImportError:
            return []
        try:
            network = pylast.LastFMNetwork(api_key=self._api_key)
            track = network.get_track(artist, title)
            top_tags = track.get_top_tags()
        except Exception:
            return []
        return [(t.item.name, int(t.weight)) for t in top_tags if t.item is not None]

    def _candidates_from_tags(self, tags: list[tuple[str, int]]) -> list[GenreCandidate]:
        counts: dict[str, int] = {}
        first_raw: dict[str, str] = {}
        for name, count in tags:
            if count <= 0 or not name:
                continue
            if _lookup_key(name) in _TAG_STOPLIST:
                continue
            canonical = self._normalizer.normalize(name)
            if canonical == UNMAPPED:
                continue
            counts[canonical] = counts.get(canonical, 0) + count
            first_raw.setdefault(canonical, name)

        if not counts:
            return []
        total = sum(counts.values())
        ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        return [
            GenreCandidate(
                canonical_genre=canonical,
                raw_label=first_raw[canonical],
                source="lastfm",
                confidence=(count / total) if total else 0.0,
            )
            for canonical, count in ordered
        ]

    # -- cache ------------------------------------------------------------

    _CACHE_SCHEMA = """
    CREATE TABLE IF NOT EXISTS lastfm_lookup (
        artist_norm   TEXT NOT NULL,
        title_norm    TEXT NOT NULL,
        payload_json  TEXT NOT NULL,
        cached_at     REAL NOT NULL,
        PRIMARY KEY (artist_norm, title_norm)
    )
    """

    def _open_cache(self) -> sqlite3.Connection:
        assert self._cache_path is not None
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._cache_path)
        conn.execute(self._CACHE_SCHEMA)
        return conn

    def _cache_get(self, artist_key: str, title_key: str) -> list[tuple[str, int]] | None:
        assert self._cache_path is not None
        with self._open_cache() as conn:
            row = conn.execute(
                "SELECT payload_json FROM lastfm_lookup WHERE artist_norm = ? AND title_norm = ?",
                (artist_key, title_key),
            ).fetchone()
        if row is None:
            return None
        return _deserialize_tags(row[0])

    def _cache_put(
        self,
        artist_key: str,
        title_key: str,
        tags: list[tuple[str, int]],
    ) -> None:
        assert self._cache_path is not None
        with self._open_cache() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO lastfm_lookup "
                "(artist_norm, title_norm, payload_json, cached_at) VALUES (?, ?, ?, ?)",
                (
                    artist_key,
                    title_key,
                    _serialize_tags(tags),
                    time.time(),
                ),
            )
            conn.commit()


def _serialize_tags(tags: list[tuple[str, int]]) -> str:
    return json.dumps([{"name": name, "count": count} for name, count in tags])


def _deserialize_tags(payload: str) -> list[tuple[str, int]]:
    data = json.loads(payload)
    return [(item["name"], int(item["count"])) for item in data]


__all__ = ["DEFAULT_MIN_INTERVAL_SEC", "LastfmFetcher", "LastfmProvider"]
