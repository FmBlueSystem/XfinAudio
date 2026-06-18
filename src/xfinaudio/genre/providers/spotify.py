"""Spotify genre provider (runtime, user-keyed).

Uses the optional ``spotipy`` library with the Client Credentials flow (no
end-user OAuth required for read-only catalog access). Returns the
artist-level genres for a track. Artist-level genres are Spotify's only
genre signal after the Nov 2024 API changes; audio features / related
artists / recommendations are no longer accessible to new apps.

All responses stay in the per-user SQLite cache; provider data never ships
in repo assets. The provider is import-guarded: missing ``spotipy`` is
fine, the provider becomes a no-op. A test-injectable ``fetcher`` callable
lets unit tests avoid the network entirely.
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

# A fetcher returns a list of artist-level genre labels (raw Spotify strings).
# Injectable for tests; raises on transient failure.
SpotifyFetcher = Callable[[str, str], list[str]]


def _lookup_key(value: str) -> str:
    return _LOOKUP_NON_ALNUM.sub(" ", value.casefold()).strip()


class SpotifyProvider:
    """Genre provider backed by Spotify's artist-level genres."""

    name = "spotify"

    def __init__(
        self,
        *,
        client_id: str = "",
        client_secret: str = "",
        fetcher: SpotifyFetcher | None = None,
        cache_path: Path | None = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
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

        # Need either credentials or an injected fetcher.
        if not (self._client_id and self._client_secret) and self._fetcher is None:
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
        # Live Spotify fetch via spotipy (import-guarded).
        try:
            import spotipy  # type: ignore[import-not-found]
            from spotipy.oauth2 import SpotifyClientCredentials  # type: ignore[import-not-found]
        except ImportError:
            return None
        try:
            auth = SpotifyClientCredentials(client_id=self._client_id, client_secret=self._client_secret)
            sp = spotipy.Spotify(auth_manager=auth)
            results = sp.search(q=f"artist:{artist} track:{title}", type="track", limit=1)
            tracks = results.get("tracks", {}).get("items", [])
            if not tracks:
                return []
            artist_id = tracks[0]["artists"][0]["id"]
            artist_info = sp.artist(artist_id)
            return [str(g) for g in artist_info.get("genres", [])]
        except Exception:
            return None

    def _candidates_from_genres(self, raw_genres: list[str]) -> list[GenreCandidate]:
        # Filter out unmapped labels.
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
        # Spotify gives no per-genre weight; distribute confidence evenly.
        confidence = 1.0 / len(canonicals)
        return [
            GenreCandidate(
                canonical_genre=canonical,
                raw_label=first_raw[canonical],
                source="spotify",
                confidence=confidence,
            )
            for canonical in canonicals
        ]

    # -- cache ------------------------------------------------------------

    _CACHE_SCHEMA = """
    CREATE TABLE IF NOT EXISTS spotify_lookup (
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
                "SELECT payload_json FROM spotify_lookup WHERE artist_norm = ? AND title_norm = ?",
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
                "INSERT OR REPLACE INTO spotify_lookup "
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


__all__ = ["SpotifyFetcher", "SpotifyProvider"]
