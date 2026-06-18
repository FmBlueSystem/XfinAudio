"""Tests for the Deezer runtime provider (PR4).

Covers spec Requirement 4 Scenarios 4.1, 4.2.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from xfinaudio.genre.providers.deezer import DeezerProvider


def _track(artist: str, title: str) -> Any:
    return type("_T", (), {"artist": artist, "title": title})()


def test_deezer_provider_name() -> None:
    provider = DeezerProvider()
    assert provider.name == "deezer"


def test_deezer_returns_canonical_candidate_from_artist_genre() -> None:
    def fetcher(artist: str, title: str) -> list[str]:
        return ["Electronic"]

    provider = DeezerProvider(fetcher=fetcher)
    candidates = provider.fetch(_track("CamelPhat", "Cola"))

    assert len(candidates) == 1
    assert candidates[0].canonical_genre == "Electronica"
    assert candidates[0].source == "deezer"
    assert candidates[0].raw_label == "Electronic"


def test_deezer_coarse_genre_collapse_dance() -> None:
    """Deezer's coarse 'Dance' bucket collapses to canonical 'Dance-Pop'."""

    def fetcher(artist: str, title: str) -> list[str]:
        return ["Dance"]

    provider = DeezerProvider(fetcher=fetcher)
    candidates = provider.fetch(_track("A", "B"))

    canonical = {c.canonical_genre for c in candidates}
    assert "Dance-Pop" in canonical


def test_deezer_filters_unmapped_coarse_genres() -> None:
    def fetcher(artist: str, title: str) -> list[str]:
        return ["qwerty noise", "Pop"]

    provider = DeezerProvider(fetcher=fetcher)
    candidates = provider.fetch(_track("A", "B"))

    assert {c.canonical_genre for c in candidates} == {"Pop"}


def test_deezer_does_not_require_api_key() -> None:
    """Deezer catalog search needs no key; provider works with just a fetcher."""

    def fetcher(artist: str, title: str) -> list[str]:
        return ["Rock"]

    provider = DeezerProvider(fetcher=fetcher)
    candidates = provider.fetch(_track("A", "B"))

    assert {c.canonical_genre for c in candidates} == {"Rock"}


def test_deezer_cache_serves_repeat_lookup(tmp_path: Path) -> None:
    calls: list[tuple[str, str]] = []

    def fetcher(artist: str, title: str) -> list[str]:
        calls.append((artist, title))
        return ["Rock"]

    cache = tmp_path / "deezer_cache.sqlite"
    provider = DeezerProvider(fetcher=fetcher, cache_path=cache)
    track = _track("A", "B")

    provider.fetch(track)
    provider.fetch(track)
    provider.fetch(track)

    assert len(calls) == 1


def test_deezer_cache_distinguishes_different_tracks(tmp_path: Path) -> None:
    calls: list[tuple[str, str]] = []

    def fetcher(artist: str, title: str) -> list[str]:
        calls.append((artist, title))
        return ["Rock"] if artist == "A" else ["Pop"]

    cache = tmp_path / "deezer_cache.sqlite"
    provider = DeezerProvider(fetcher=fetcher, cache_path=cache)

    provider.fetch(_track("A", "T1"))
    provider.fetch(_track("B", "T1"))
    provider.fetch(_track("A", "T1"))  # cached

    assert len(calls) == 2


def test_deezer_fetcher_exception_is_isolated() -> None:
    def bad_fetcher(artist: str, title: str) -> list[str]:
        raise RuntimeError("deezer down")

    provider = DeezerProvider(fetcher=bad_fetcher)
    assert provider.fetch(_track("A", "B")) == []


def test_deezer_transient_failure_is_not_cached(tmp_path: Path) -> None:
    calls = 0

    def fetcher(artist: str, title: str) -> list[str]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("deezer down")
        return ["Rock"]

    provider = DeezerProvider(fetcher=fetcher, cache_path=tmp_path / "d.sqlite")
    track = _track("A", "B")

    assert provider.fetch(track) == []
    assert {candidate.canonical_genre for candidate in provider.fetch(track)} == {"Rock"}
    assert calls == 2


def test_deezer_empty_artist_or_title_returns_no_candidates() -> None:
    def fetcher(artist: str, title: str) -> list[str]:
        return ["Rock"]

    provider = DeezerProvider(fetcher=fetcher)
    assert provider.fetch(_track("", "Title")) == []
    assert provider.fetch(_track("Artist", "")) == []


def test_deezer_provider_satisfies_protocol() -> None:
    from xfinaudio.genre.providers.base import GenreProvider

    provider = DeezerProvider()
    assert isinstance(provider, GenreProvider)


def test_deezer_empty_genres_list_yields_no_candidates(tmp_path: Path) -> None:
    def fetcher(artist: str, title: str) -> list[str]:
        return []

    provider = DeezerProvider(fetcher=fetcher, cache_path=tmp_path / "c.sqlite")
    assert provider.fetch(_track("Nobody", "Nothing")) == []


def test_deezer_confidence_distributes_evenly() -> None:
    def fetcher(artist: str, title: str) -> list[str]:
        return ["Rock", "Pop"]

    provider = DeezerProvider(fetcher=fetcher)
    candidates = provider.fetch(_track("A", "B"))

    by_genre = {c.canonical_genre: c for c in candidates}
    assert abs(by_genre["Rock"].confidence - 0.5) < 1e-9
    assert abs(by_genre["Pop"].confidence - 0.5) < 1e-9
