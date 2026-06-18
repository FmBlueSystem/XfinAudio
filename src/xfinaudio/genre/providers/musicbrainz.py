"""MusicBrainz genre provider with a 1 req/s throttle and per-user cache.

Maps MusicBrainz curated genres and denoised folksonomy tags onto the
canonical genre taxonomy. The live fetcher uses the optional ``musicbrainzngs``
library behind a 1 request/second throttle. The provider performs no audio
mutation and no DSP; identity lookup uses artist+title only.

Schema
------
``mb_lookup(artist_norm, title_norm, payload_json, cached_at)`` stores the
serialized :class:`MBResponse` so repeat lookups avoid any network call.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xfinaudio.genre.models import GenreCandidate
from xfinaudio.genre.normalizer import UNMAPPED, GenreNormalizer

_LOOKUP_NON_ALNUM = re.compile(r"[^a-z0-9]+")
DEFAULT_MIN_INTERVAL_SEC = 1.0

# Stoplist for non-genre folksonomy noise that should never become a candidate.
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

# A fetcher is any callable that takes (artist, title) and returns a parsed
# MBResponse (or None when nothing was found / lookup failed).
MusicBrainzFetcher = Callable[[str, str], "MBResponse | None"]


def _lookup_key(value: str) -> str:
    """Return a case- and punctuation-insensitive lookup key."""
    return _LOOKUP_NON_ALNUM.sub(" ", value.casefold()).strip()


@dataclass(frozen=True)
class MBGenreTag:
    """A single MusicBrainz genre or tag with its vote count."""

    name: str
    count: int


@dataclass(frozen=True)
class MBResponse:
    """Parsed MusicBrainz response: curated genres and folksonomy tags."""

    genres: tuple[MBGenreTag, ...]
    tags: tuple[MBGenreTag, ...]


# ---------------------------------------------------------------------------
# Throttle
# ---------------------------------------------------------------------------


class ThrottledFetcher:
    """Wrap a fetcher with a minimum interval between successive calls.

    Production: ``time.sleep`` blocks until the interval has elapsed, so the
    MusicBrainz public service's 1 req/s rate limit is respected.
    Tests: inject a fake clock and a sleeper that advances the clock; this
    exercises the same code path deterministically.
    """

    def __init__(
        self,
        fetcher: MusicBrainzFetcher,
        *,
        min_interval_sec: float = DEFAULT_MIN_INTERVAL_SEC,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._min_interval = min_interval_sec
        self._clock = clock if clock is not None else time.monotonic
        self._sleep = sleep if sleep is not None else time.sleep
        self._last_call: float = -1e18

    def __call__(self, artist: str, title: str) -> MBResponse | None:
        now = self._clock()
        wait = self._min_interval - (now - self._last_call)
        if wait > 0:
            self._sleep(wait)
        self._last_call = self._clock()
        return self._fetcher(artist, title)


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class MusicBrainzProvider:
    """Genre provider sourced from MusicBrainz with a per-user SQLite cache."""

    name = "musicbrainz"

    def __init__(
        self,
        *,
        fetcher: MusicBrainzFetcher,
        cache_path: Path | None = None,
    ) -> None:
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

        response = self._lookup(artist_key, title_key)
        if response is None:
            return []

        return self._candidates_from_response(response)

    # -- internals --------------------------------------------------------

    def _lookup(self, artist_key: str, title_key: str) -> MBResponse | None:
        """Return a response from cache when present, otherwise fetch + cache."""
        if self._cache_path is not None:
            cached = self._cache_get(artist_key, title_key)
            if cached is not None:
                return cached

        try:
            response = self._fetcher(_raw_artist_for(artist_key), _raw_title_for(title_key))
        except Exception:
            return None

        if response is not None and self._cache_path is not None:
            self._cache_put(artist_key, title_key, response)
        return response

    def _candidates_from_response(self, response: MBResponse) -> list[GenreCandidate]:
        counts: dict[str, int] = {}
        first_raw: dict[str, str] = {}
        source_for: dict[str, str] = {}

        for entry, source_label in (
            (response.genres, "musicbrainz_genres"),
            (response.tags, "musicbrainz_tags"),
        ):
            for tag in entry:
                if tag.count <= 0:
                    continue
                if source_label == "musicbrainz_tags" and _lookup_key(tag.name) in _TAG_STOPLIST:
                    continue
                canonical = self._normalizer.normalize(tag.name)
                if canonical == UNMAPPED:
                    continue
                counts[canonical] = counts.get(canonical, 0) + tag.count
                first_raw.setdefault(canonical, tag.name)
                source_for.setdefault(canonical, source_label)

        if not counts:
            return []
        total = sum(counts.values())
        ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        return [
            GenreCandidate(
                canonical_genre=canonical,
                raw_label=first_raw[canonical],
                source=source_for[canonical],
                confidence=(count / total) if total else 0.0,
            )
            for canonical, count in ordered
        ]

    # -- cache ------------------------------------------------------------

    _CACHE_SCHEMA = """
    CREATE TABLE IF NOT EXISTS mb_lookup (
        artist_norm   TEXT NOT NULL,
        title_norm    TEXT NOT NULL,
        payload_json  TEXT NOT NULL,
        cached_at     REAL NOT NULL,
        PRIMARY KEY (artist_norm, title_norm)
    )
    """

    def _open_cache(self) -> sqlite3.Connection:
        """Open the cache, creating parent dir + schema on demand."""
        assert self._cache_path is not None
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._cache_path)
        conn.execute(self._CACHE_SCHEMA)
        return conn

    def _cache_get(self, artist_key: str, title_key: str) -> MBResponse | None:
        assert self._cache_path is not None
        with self._open_cache() as conn:
            row = conn.execute(
                "SELECT payload_json FROM mb_lookup WHERE artist_norm = ? AND title_norm = ?",
                (artist_key, title_key),
            ).fetchone()
        if row is None:
            return None
        return _deserialize_response(row[0])

    def _cache_put(self, artist_key: str, title_key: str, response: MBResponse) -> None:
        assert self._cache_path is not None
        with self._open_cache() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO mb_lookup "
                "(artist_norm, title_norm, payload_json, cached_at) VALUES (?, ?, ?, ?)",
                (
                    artist_key,
                    title_key,
                    _serialize_response(response),
                    time.time(),
                ),
            )
            conn.commit()


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _serialize_response(response: MBResponse) -> str:
    return json.dumps(
        {
            "genres": [{"name": g.name, "count": g.count} for g in response.genres],
            "tags": [{"name": t.name, "count": t.count} for t in response.tags],
        }
    )


def _deserialize_response(payload: str) -> MBResponse:
    data: dict[str, list[dict[str, Any]]] = json.loads(payload)
    return MBResponse(
        genres=tuple(MBGenreTag(name=g["name"], count=int(g["count"])) for g in data.get("genres", [])),
        tags=tuple(MBGenreTag(name=t["name"], count=int(t["count"])) for t in data.get("tags", [])),
    )


# ---------------------------------------------------------------------------
# Live fetcher (import-guarded)
# ---------------------------------------------------------------------------


def make_live_fetcher(
    app_name: str = "xfinaudio",
    app_version: str = "1.0",
    *,
    min_interval_sec: float = DEFAULT_MIN_INTERVAL_SEC,
) -> MusicBrainzFetcher:
    """Return a :class:`ThrottledFetcher` backed by the ``musicbrainzngs`` library.

    Raises ``ImportError`` with a clear message when ``musicbrainzngs`` is not
    installed; the enrichment service treats a missing live fetcher as a
    disabled provider (no network is ever attempted).
    """
    try:
        import musicbrainzngs  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised in production
        raise ImportError(
            "musicbrainzngs is required for the live MusicBrainz provider; "
            "install it or disable the musicbrainz provider in settings."
        ) from exc

    musicbrainzngs.set_useragent(app_name, app_version)

    def _fetch(artist: str, title: str) -> MBResponse | None:
        try:
            search = musicbrainzngs.search_recordings(artist=artist, recording=title, limit=1)
        except Exception:
            return None
        recordings = search.get("recording-list") or []
        if not recordings:
            return None
        recording_id = recordings[0].get("id")
        if not recording_id:
            return None
        try:
            detail = musicbrainzngs.get_recording_by_id(recording_id, includes=["genres", "tags"])
        except Exception:
            return None
        rec = detail.get("recording") or {}

        def _entries(key: str) -> tuple[MBGenreTag, ...]:
            return tuple(
                MBGenreTag(
                    name=str(item.get("name", "")).strip(),
                    count=int(item.get("count", 0) or 0),
                )
                for item in (rec.get(key) or [])
                if item.get("name")
            )

        return MBResponse(genres=_entries("genre-list"), tags=_entries("tag-list"))

    return ThrottledFetcher(_fetch, min_interval_sec=min_interval_sec)


# ---------------------------------------------------------------------------
# Tiny raw-value roundtrip helpers
# ---------------------------------------------------------------------------


def _raw_artist_for(key: str) -> str:
    """Recover a presentable artist string from a lookup key.

    The provider fetches by the raw artist/title passed by callers; the cache
    keys are derived from these via :func:`_lookup_key`. Since the cache only
    needs the key, this helper is a placeholder for cases where the fetcher
    expects the raw value.
    """
    return key


def _raw_title_for(key: str) -> str:
    """See :func:`_raw_artist_for`."""
    return key


__all__ = [
    "DEFAULT_MIN_INTERVAL_SEC",
    "MBGenreTag",
    "MBResponse",
    "MusicBrainzFetcher",
    "MusicBrainzProvider",
    "ThrottledFetcher",
    "make_live_fetcher",
]
