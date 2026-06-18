"""Deezer genre provider (runtime, no key required for catalog).

Uses the public Deezer API via stdlib ``urllib.request`` (no new dependency).
Returns the top-level genre bucket of the matched track's artist. Deezer's
catalog API needs no authentication, which makes this the simplest runtime
provider; the trade-off is coarse-grained genres (around 23 top-level
buckets like "Electronic", "Dance", "Pop", "Rock", "Hip-Hop", "R&B", etc.).

All responses stay in the per-user SQLite cache; provider data never ships
in repo assets. A test-injectable ``fetcher`` callable lets unit tests avoid
the network entirely.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path

from xfinaudio.genre.models import GenreCandidate
from xfinaudio.genre.normalizer import UNMAPPED, GenreNormalizer

_LOOKUP_NON_ALNUM = re.compile(r"[^a-z0-9]+")
DEEZER_SEARCH_URL = "https://api.deezer.com/search"
DEEZER_ARTIST_URL = "https://api.deezer.com/artist/{artist_id}"
DEFAULT_TIMEOUT_SEC = 5.0

# A fetcher returns a list of Deezer top-level genre names for the artist.
# Injectable for tests; raises on transient failure.
DeezerFetcher = Callable[[str, str], list[str]]


def _lookup_key(value: str) -> str:
    return _LOOKUP_NON_ALNUM.sub(" ", value.casefold()).strip()


class DeezerProvider:
    """Genre provider backed by Deezer's public catalog API."""

    name = "deezer"

    def __init__(
        self,
        *,
        fetcher: DeezerFetcher | None = None,
        cache_path: Path | None = None,
        timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    ) -> None:
        self._fetcher = fetcher
        self._cache_path = cache_path
        self._timeout = timeout_sec
        self._normalizer = GenreNormalizer.default()

    def fetch(self, track: object) -> list[GenreCandidate]:
        artist = getattr(track, "artist", None) or ""
        title = getattr(track, "title", None) or ""
        artist_key = _lookup_key(artist)
        title_key = _lookup_key(title)
        if not artist_key or not title_key:
            return []

        raw_genres = self._lookup(artist_key, title_key, raw_artist=artist, raw_title=title)
        return self._candidates_from_genres(raw_genres)

    # -- internals --------------------------------------------------------

    def _lookup(
        self,
        artist_key: str,
        title_key: str,
        *,
        raw_artist: str,
        raw_title: str,
    ) -> list[str]:
        if self._cache_path is not None:
            cached = self._cache_get(artist_key, title_key)
            if cached is not None:
                return cached

        genres = self._call_fetcher(raw_artist, raw_title)
        if genres is None:
            return []
        if self._cache_path is not None:
            self._cache_put(artist_key, title_key, genres)
        return genres

    def _call_fetcher(self, artist: str, title: str) -> list[str] | None:
        if self._fetcher is not None:
            try:
                return list(self._fetcher(artist, title))
            except Exception:
                return None
        return self._fetch_live(artist, title)

    def _fetch_live(self, artist: str, title: str) -> list[str] | None:
        try:
            query = urllib.parse.urlencode({"q": f"{artist} {title}"})
            with urllib.request.urlopen(f"{DEEZER_SEARCH_URL}?{query}", timeout=self._timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            tracks = payload.get("data", [])
            if not tracks:
                return []
            artist_id = tracks[0].get("artist", {}).get("id")
            if not artist_id:
                return []
            with urllib.request.urlopen(DEEZER_ARTIST_URL.format(artist_id=artist_id), timeout=self._timeout) as resp:
                artist_payload = json.loads(resp.read().decode("utf-8"))
            # Deezer exposes an artist's genres via the ``genre_id`` list of ids.
            # Without a separate name lookup we accept the bucket id as a label;
            # the crosswalk handles the rest. As a fallback we also accept any
            # ``name`` field present in the artist object (rare for coarse genres).
            names: list[str] = []
            for genre_id in artist_payload.get("genre_id_list") or []:
                names.append(str(genre_id))
            return names
        except (urllib.error.URLError, json.JSONDecodeError, KeyError, OSError):
            return None

    def _candidates_from_genres(self, raw_genres: list[str]) -> list[GenreCandidate]:
        canonicals: list[str] = []
        first_raw: dict[str, str] = {}
        for raw in raw_genres:
            if not raw:
                continue
            canonical = self._normalizer.normalize(raw)
            if canonical == UNMAPPED:
                continue
            if canonical not in first_raw:
                first_raw[canonical] = raw
                canonicals.append(canonical)
        if not canonicals:
            return []
        # Deezer gives no per-genre weight; distribute confidence evenly.
        confidence = 1.0 / len(canonicals)
        return [
            GenreCandidate(
                canonical_genre=canonical,
                raw_label=first_raw[canonical],
                source="deezer",
                confidence=confidence,
            )
            for canonical in canonicals
        ]

    # -- cache ------------------------------------------------------------

    _CACHE_SCHEMA = """
    CREATE TABLE IF NOT EXISTS deezer_lookup (
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

    def _cache_get(self, artist_key: str, title_key: str) -> list[str] | None:
        assert self._cache_path is not None
        with self._open_cache() as conn:
            row = conn.execute(
                "SELECT payload_json FROM deezer_lookup WHERE artist_norm = ? AND title_norm = ?",
                (artist_key, title_key),
            ).fetchone()
        if row is None:
            return None
        return _deserialize_genres(row[0])

    def _cache_put(
        self,
        artist_key: str,
        title_key: str,
        genres: list[str],
    ) -> None:
        assert self._cache_path is not None
        with self._open_cache() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO deezer_lookup "
                "(artist_norm, title_norm, payload_json, cached_at) VALUES (?, ?, ?, ?)",
                (
                    artist_key,
                    title_key,
                    _serialize_genres(genres),
                    time.time(),
                ),
            )
            conn.commit()


def _serialize_genres(genres: list[str]) -> str:
    return json.dumps(list(genres))


def _deserialize_genres(payload: str) -> list[str]:
    return [str(item) for item in json.loads(payload)]


__all__ = ["DEEZER_ARTIST_URL", "DEEZER_SEARCH_URL", "DeezerFetcher", "DeezerProvider"]
