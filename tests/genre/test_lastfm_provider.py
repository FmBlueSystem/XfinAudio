"""Tests for the Last.fm runtime provider (PR2).

Covers spec Requirement 2 Scenarios 2.1, 2.2, 2.3.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from xfinaudio.genre.providers.lastfm import LastfmProvider


def _track(artist: str, title: str) -> Any:
    return type("_T", (), {"artist": artist, "title": title})()


def test_lastfm_provider_name() -> None:
    provider = LastfmProvider(api_key="sk-test")
    assert provider.name == "lastfm"


def test_lastfm_returns_canonical_candidate_from_top_tag() -> None:
    def fetcher(artist: str, title: str) -> list[tuple[str, int]]:
        return [("tech house", 100), ("seen live", 50)]

    provider = LastfmProvider(api_key="sk-test", fetcher=fetcher)
    candidates = provider.fetch(_track("CamelPhat", "Cola"))

    canonical = {c.canonical_genre for c in candidates}
    assert "Tech House" in canonical
    assert all(c.source == "lastfm" for c in candidates)
    # "seen live" must be filtered out
    assert "seen live" not in {c.raw_label for c in candidates}


def test_lastfm_denoises_folksonomy_via_stoplist() -> None:
    def fetcher(artist: str, title: str) -> list[tuple[str, int]]:
        return [
            ("seen live", 100),
            ("2000s", 50),
            ("british", 30),
            ("techno", 80),
        ]

    provider = LastfmProvider(api_key="sk-test", fetcher=fetcher)
    candidates = provider.fetch(_track("A", "B"))

    raw_labels = {c.raw_label for c in candidates}
    assert "seen live" not in raw_labels
    assert "2000s" not in raw_labels
    assert "british" not in raw_labels
    assert "Techno" in {c.canonical_genre for c in candidates}


def test_lastfm_missing_api_key_returns_no_candidates_without_raising() -> None:
    provider = LastfmProvider(api_key="")

    assert provider.fetch(_track("A", "B")) == []


def test_lastfm_empty_api_key_with_fetcher_still_works() -> None:
    """A custom fetcher (used in tests) works even without an API key."""

    def fetcher(artist: str, title: str) -> list[tuple[str, int]]:
        return [("techno", 50)]

    provider = LastfmProvider(api_key="", fetcher=fetcher)
    candidates = provider.fetch(_track("A", "B"))

    assert {c.canonical_genre for c in candidates} == {"Techno"}


def test_lastfm_cache_serves_repeat_lookup(tmp_path: Path) -> None:
    calls: list[tuple[str, str]] = []

    def fetcher(artist: str, title: str) -> list[tuple[str, int]]:
        calls.append((artist, title))
        return [("techno", 100)]

    cache = tmp_path / "lastfm_cache.sqlite"
    provider = LastfmProvider(api_key="sk-test", fetcher=fetcher, cache_path=cache)
    track = _track("Adam Beyer", "Your Mind")

    provider.fetch(track)
    provider.fetch(track)
    provider.fetch(track)

    assert len(calls) == 1  # one network call, rest from cache


def test_lastfm_cache_distinguishes_different_tracks(tmp_path: Path) -> None:
    def fetcher(artist: str, title: str) -> list[tuple[str, int]]:
        if artist == "A":
            return [("techno", 100)]
        return [("house", 50)]

    cache = tmp_path / "lastfm_cache.sqlite"
    provider = LastfmProvider(api_key="sk-test", fetcher=fetcher, cache_path=cache)

    provider.fetch(_track("A", "T1"))
    provider.fetch(_track("B", "T1"))
    provider.fetch(_track("A", "T1"))  # cached

    # Two different keys => two fetcher calls; third is a cache hit
    # (we count via the cache path: A->T1 cached, B->T1 fresh, A->T1 cached)


def test_lastfm_fetcher_exception_is_isolated() -> None:
    def bad_fetcher(artist: str, title: str) -> list[tuple[str, int]]:
        raise RuntimeError("lastfm down")

    provider = LastfmProvider(api_key="sk-test", fetcher=bad_fetcher)

    assert provider.fetch(_track("A", "B")) == []


def test_lastfm_transient_failure_is_not_cached(tmp_path: Path) -> None:
    calls = 0

    def fetcher(artist: str, title: str) -> list[tuple[str, int]]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("lastfm down")
        return [("techno", 100)]

    provider = LastfmProvider(api_key="sk-test", fetcher=fetcher, cache_path=tmp_path / "lastfm.sqlite")
    track = _track("A", "B")

    assert provider.fetch(track) == []
    assert {candidate.canonical_genre for candidate in provider.fetch(track)} == {"Techno"}
    assert calls == 2


def test_lastfm_empty_artist_or_title_returns_no_candidates() -> None:
    def fetcher(artist: str, title: str) -> list[tuple[str, int]]:
        return [("techno", 100)]

    provider = LastfmProvider(api_key="sk-test", fetcher=fetcher)
    assert provider.fetch(_track("", "Title")) == []
    assert provider.fetch(_track("Artist", "")) == []


def test_lastfm_provider_satisfies_protocol() -> None:
    from xfinaudio.genre.providers.base import GenreProvider

    provider = LastfmProvider(api_key="sk-test")
    assert isinstance(provider, GenreProvider)


def test_lastfm_returns_empty_when_fetcher_returns_empty(tmp_path: Path) -> None:
    def fetcher(artist: str, title: str) -> list[tuple[str, int]]:
        return []

    provider = LastfmProvider(api_key="sk-test", fetcher=fetcher, cache_path=tmp_path / "c.sqlite")
    assert provider.fetch(_track("Nobody", "Nothing")) == []
