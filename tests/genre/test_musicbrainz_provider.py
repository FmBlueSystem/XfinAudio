"""Tests for the MusicBrainz genre provider (PR4).

Covers spec Requirement 4 Scenarios 4.1 (MB genres/tags -> canonical candidates
with confidence from vote ratio, denoised tags) and 4.2 (1 req/s throttle via
injectable clock, cache hit avoids network).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from xfinaudio.genre.providers.musicbrainz import (
    MBGenreTag,
    MBResponse,
    MusicBrainzProvider,
    ThrottledFetcher,
    make_live_fetcher,
)


class _FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@dataclass
class _RecordingFetcher:
    responses: list[MBResponse | None]
    calls: list[tuple[str, str]] = field(default_factory=list)
    _index: int = 0

    def __call__(self, artist: str, title: str) -> MBResponse | None:
        self.calls.append((artist, title))
        if self._index >= len(self.responses):
            return None
        result = self.responses[self._index]
        self._index += 1
        return result


def _track(artist: str, title: str) -> Any:
    return type("_T", (), {"artist": artist, "title": title})()


def test_provider_returns_canonical_candidate_from_mb_genre() -> None:
    fetcher = _RecordingFetcher(
        responses=[
            MBResponse(
                genres=(MBGenreTag(name="techno", count=10),),
                tags=(),
            )
        ]
    )
    provider = MusicBrainzProvider(fetcher=fetcher, cache_path=None)

    candidates = provider.fetch(_track("Adam Beyer", "Your Mind"))

    assert {c.canonical_genre for c in candidates} == {"Techno"}
    assert all(c.source == "musicbrainz_genres" for c in candidates)
    assert all(0.0 <= c.confidence <= 1.0 for c in candidates)


def test_provider_confidence_reflects_vote_ratio() -> None:
    fetcher = _RecordingFetcher(
        responses=[
            MBResponse(
                genres=(
                    MBGenreTag(name="techno", count=8),
                    MBGenreTag(name="electronic", count=2),
                ),
                tags=(),
            )
        ]
    )
    provider = MusicBrainzProvider(fetcher=fetcher, cache_path=None)

    candidates = provider.fetch(_track("A", "T"))

    by_genre = {c.canonical_genre: c for c in candidates}
    assert by_genre["Techno"].confidence > by_genre["Electronica"].confidence
    assert abs(by_genre["Techno"].confidence - 0.8) < 1e-9
    assert abs(by_genre["Electronica"].confidence - 0.2) < 1e-9


def test_provider_denoises_tags_via_stoplist() -> None:
    fetcher = _RecordingFetcher(
        responses=[
            MBResponse(
                genres=(),
                tags=(
                    MBGenreTag(name="seen live", count=100),
                    MBGenreTag(name="2000s", count=50),
                    MBGenreTag(name="british", count=30),
                    MBGenreTag(name="electronic", count=30),
                ),
            )
        ]
    )
    provider = MusicBrainzProvider(fetcher=fetcher, cache_path=None)

    candidates = provider.fetch(_track("A", "T"))

    raw_labels = {c.raw_label for c in candidates}
    assert "seen live" not in raw_labels
    assert "2000s" not in raw_labels
    assert "british" not in raw_labels
    assert "Electronica" in {c.canonical_genre for c in candidates}
    assert all(c.source == "musicbrainz_tags" for c in candidates)


def test_provider_combines_genre_and_tag_votes_per_canonical() -> None:
    fetcher = _RecordingFetcher(
        responses=[
            MBResponse(
                genres=(MBGenreTag(name="techno", count=4),),
                tags=(MBGenreTag(name="techno", count=6),),
            )
        ]
    )
    provider = MusicBrainzProvider(fetcher=fetcher, cache_path=None)

    candidates = provider.fetch(_track("A", "T"))

    assert len(candidates) == 1
    assert candidates[0].canonical_genre == "Techno"
    assert abs(candidates[0].confidence - 1.0) < 1e-9


def test_provider_returns_empty_when_fetcher_returns_none() -> None:
    fetcher = _RecordingFetcher(responses=[None])
    provider = MusicBrainzProvider(fetcher=fetcher, cache_path=None)

    assert provider.fetch(_track("Nobody", "Nothing")) == []


def test_provider_isolates_fetcher_exception() -> None:
    def bad_fetcher(artist: str, title: str) -> MBResponse | None:
        raise RuntimeError("network down")

    provider = MusicBrainzProvider(fetcher=bad_fetcher, cache_path=None)

    assert provider.fetch(_track("A", "T")) == []


def test_provider_returns_empty_for_blank_artist_or_title() -> None:
    fetcher = _RecordingFetcher(responses=[None])
    provider = MusicBrainzProvider(fetcher=fetcher, cache_path=None)

    assert provider.fetch(_track("", "Title")) == []
    assert provider.fetch(_track("Artist", "")) == []
    assert provider.fetch(_track("   ", "  ")) == []


def test_throttle_sleeps_when_interval_not_elapsed() -> None:
    clock = _FakeClock()
    sleep_log: list[float] = []

    def fake_sleep(secs: float) -> None:
        sleep_log.append(secs)
        clock.advance(secs)

    fetcher = _RecordingFetcher(
        responses=[
            MBResponse(genres=(), tags=()),
            MBResponse(genres=(), tags=()),
            MBResponse(genres=(), tags=()),
        ]
    )
    throttled: Callable[[str, str], MBResponse | None] = ThrottledFetcher(
        fetcher,
        min_interval_sec=1.0,
        clock=clock,
        sleep=fake_sleep,
    )

    throttled("A", "B")
    throttled("A", "B")
    throttled("A", "B")

    assert len(fetcher.calls) == 3
    assert sleep_log == [1.0, 1.0]


def test_throttle_does_not_sleep_after_interval_elapsed() -> None:
    clock = _FakeClock()
    sleep_log: list[float] = []

    def fake_sleep(secs: float) -> None:
        sleep_log.append(secs)
        clock.advance(secs)

    fetcher = _RecordingFetcher(responses=[MBResponse(genres=(), tags=())])
    throttled = ThrottledFetcher(
        fetcher,
        min_interval_sec=1.0,
        clock=clock,
        sleep=fake_sleep,
    )

    throttled("A", "B")
    clock.advance(5.0)
    throttled("A", "B")

    assert sleep_log == []


def test_cache_serves_repeat_lookup_without_calling_fetcher(tmp_path) -> None:
    fetcher = _RecordingFetcher(
        responses=[
            MBResponse(
                genres=(MBGenreTag(name="techno", count=5),),
                tags=(),
            )
        ]
    )
    cache = tmp_path / "mb_cache.sqlite"
    provider = MusicBrainzProvider(fetcher=fetcher, cache_path=cache)

    track = _track("Adam Beyer", "Your Mind")
    provider.fetch(track)
    provider.fetch(track)
    provider.fetch(track)

    assert len(fetcher.calls) == 1


def test_cache_distinguishes_different_tracks(tmp_path) -> None:
    fetcher = _RecordingFetcher(
        responses=[
            MBResponse(genres=(MBGenreTag(name="techno", count=5),), tags=()),
            MBResponse(genres=(MBGenreTag(name="house", count=3),), tags=()),
        ]
    )
    cache = tmp_path / "mb_cache.sqlite"
    provider = MusicBrainzProvider(fetcher=fetcher, cache_path=cache)

    provider.fetch(_track("A", "T1"))
    provider.fetch(_track("B", "T2"))
    provider.fetch(_track("A", "T1"))

    assert len(fetcher.calls) == 2


def test_cache_creates_parent_dir(tmp_path) -> None:
    fetcher = _RecordingFetcher(responses=[MBResponse(genres=(MBGenreTag(name="techno", count=1),), tags=())])
    cache = tmp_path / "nested" / "dir" / "mb_cache.sqlite"
    provider = MusicBrainzProvider(fetcher=fetcher, cache_path=cache)

    provider.fetch(_track("A", "T"))

    assert cache.exists()


def test_provider_name_is_musicbrainz() -> None:
    provider = MusicBrainzProvider(fetcher=_RecordingFetcher(responses=[]), cache_path=None)
    assert provider.name == "musicbrainz"


def test_provider_satisfies_protocol() -> None:
    from xfinaudio.genre.providers.base import GenreProvider

    provider = MusicBrainzProvider(fetcher=_RecordingFetcher(responses=[]), cache_path=None)
    assert isinstance(provider, GenreProvider)


def test_make_live_fetcher_returns_callable() -> None:
    fetcher = make_live_fetcher("xfinaudio", "1.0")
    assert callable(fetcher)
