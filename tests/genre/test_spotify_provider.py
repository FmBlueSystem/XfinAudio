"""Tests for the Spotify runtime provider (PR3).

Covers spec Requirement 3 Scenarios 3.1, 3.2.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from xfinaudio.genre.providers.spotify import SpotifyProvider


def _track(artist: str, title: str) -> Any:
    return type("_T", (), {"artist": artist, "title": title})()


def test_spotify_provider_name() -> None:
    provider = SpotifyProvider(client_id="id", client_secret="sec")
    assert provider.name == "spotify"


def test_spotify_returns_canonical_candidates_from_artist_genres() -> None:
    def fetcher(artist: str, title: str) -> list[str]:
        return ["tech house", "house"]

    provider = SpotifyProvider(client_id="id", client_secret="sec", fetcher=fetcher)
    candidates = provider.fetch(_track("CamelPhat", "Cola"))

    canonical = {c.canonical_genre for c in candidates}
    assert "Tech House" in canonical
    assert "House" in canonical
    assert all(c.source == "spotify" for c in candidates)


def test_spotify_confidence_distributes_evenly_across_genres() -> None:
    """When the API returns N genres, each gets confidence 1/N (even split)."""

    def fetcher(artist: str, title: str) -> list[str]:
        return ["techno", "house"]

    provider = SpotifyProvider(client_id="id", client_secret="sec", fetcher=fetcher)
    candidates = provider.fetch(_track("A", "B"))

    by_genre = {c.canonical_genre: c for c in candidates}
    assert abs(by_genre["Techno"].confidence - 0.5) < 1e-9
    assert abs(by_genre["House"].confidence - 0.5) < 1e-9


def test_spotify_filters_unmapped_genres() -> None:
    """Genres that don't map to canonical via the crosswalk are dropped."""

    def fetcher(artist: str, title: str) -> list[str]:
        return ["qwerty noise", "house"]  # first one is unknown

    provider = SpotifyProvider(client_id="id", client_secret="sec", fetcher=fetcher)
    candidates = provider.fetch(_track("A", "B"))

    assert {c.canonical_genre for c in candidates} == {"House"}


def test_spotify_missing_credentials_returns_no_candidates_without_raising() -> None:
    provider = SpotifyProvider(client_id="", client_secret="")

    assert provider.fetch(_track("A", "B")) == []


def test_spotify_empty_credentials_with_fetcher_still_works() -> None:
    """A custom fetcher (used in tests) works even without credentials."""

    def fetcher(artist: str, title: str) -> list[str]:
        return ["techno"]

    provider = SpotifyProvider(client_id="", client_secret="", fetcher=fetcher)
    candidates = provider.fetch(_track("A", "B"))

    assert {c.canonical_genre for c in candidates} == {"Techno"}


def test_spotify_cache_serves_repeat_lookup(tmp_path: Path) -> None:
    calls: list[tuple[str, str]] = []

    def fetcher(artist: str, title: str) -> list[str]:
        calls.append((artist, title))
        return ["techno"]

    cache = tmp_path / "spotify_cache.sqlite"
    provider = SpotifyProvider(client_id="id", client_secret="sec", fetcher=fetcher, cache_path=cache)
    track = _track("Adam Beyer", "Your Mind")

    provider.fetch(track)
    provider.fetch(track)
    provider.fetch(track)

    assert len(calls) == 1


def test_spotify_cache_distinguishes_different_tracks(tmp_path: Path) -> None:
    calls: list[tuple[str, str]] = []

    def fetcher(artist: str, title: str) -> list[str]:
        calls.append((artist, title))
        return ["techno"] if artist == "A" else ["house"]

    cache = tmp_path / "spotify_cache.sqlite"
    provider = SpotifyProvider(client_id="id", client_secret="sec", fetcher=fetcher, cache_path=cache)

    provider.fetch(_track("A", "T1"))
    provider.fetch(_track("B", "T1"))
    provider.fetch(_track("A", "T1"))  # cached

    # Two distinct keys => two fetcher calls; the third is a cache hit.
    assert len(calls) == 2


def test_spotify_fetcher_exception_is_isolated() -> None:
    def bad_fetcher(artist: str, title: str) -> list[str]:
        raise RuntimeError("spotify down")

    provider = SpotifyProvider(client_id="id", client_secret="sec", fetcher=bad_fetcher)
    assert provider.fetch(_track("A", "B")) == []


def test_spotify_transient_failure_is_not_cached(tmp_path: Path) -> None:
    calls = 0

    def fetcher(artist: str, title: str) -> list[str]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("spotify down")
        return ["techno"]

    provider = SpotifyProvider(client_id="id", client_secret="sec", fetcher=fetcher, cache_path=tmp_path / "s.sqlite")
    track = _track("A", "B")

    assert provider.fetch(track) == []
    assert {candidate.canonical_genre for candidate in provider.fetch(track)} == {"Techno"}
    assert calls == 2


def test_spotify_empty_artist_or_title_returns_no_candidates() -> None:
    def fetcher(artist: str, title: str) -> list[str]:
        return ["techno"]

    provider = SpotifyProvider(client_id="id", client_secret="sec", fetcher=fetcher)
    assert provider.fetch(_track("", "Title")) == []
    assert provider.fetch(_track("Artist", "")) == []


def test_spotify_provider_satisfies_protocol() -> None:
    from xfinaudio.genre.providers.base import GenreProvider

    provider = SpotifyProvider(client_id="id", client_secret="sec")
    assert isinstance(provider, GenreProvider)


def test_spotify_empty_genres_list_yields_no_candidates(tmp_path: Path) -> None:
    def fetcher(artist: str, title: str) -> list[str]:
        return []

    provider = SpotifyProvider(
        client_id="id",
        client_secret="sec",
        fetcher=fetcher,
        cache_path=tmp_path / "c.sqlite",
    )
    assert provider.fetch(_track("Nobody", "Nothing")) == []
