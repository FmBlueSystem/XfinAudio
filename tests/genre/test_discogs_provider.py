"""Tests for the Discogs provider fetch path (PR3, Task 3.2).

Covers spec Requirement 3 Scenarios 3.1 (Discogs styles -> canonical
candidates) and 3.2 (offline operation, no network). All tests run against a
local cache populated from an XML fixture; no network is ever involved.
"""

from __future__ import annotations

from pathlib import Path

from xfinaudio.genre.providers.discogs import (
    DiscogsProvider,
    ingest_discogs_dump,
)

FIXTURE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<discogs>
  <releases>
    <release id="100">
      <artists><artist><name>CamelPhat</name></artist></artists>
      <title>Cola</title>
      <styles>
        <style>Tech House</style>
        <style>Deep House</style>
      </styles>
    </release>
    <release id="101">
      <artists><artist><name>Adam Beyer</name></artist></artists>
      <title>Your Mind</title>
      <styles>
        <style>Techno</style>
      </styles>
    </release>
  </releases>
</discogs>
"""


def _seed_cache(tmp_path: Path) -> Path:
    fixture = tmp_path / "discogs.xml"
    fixture.write_text(FIXTURE_XML, encoding="utf-8")
    cache = tmp_path / "discogs_cache.sqlite"
    ingest_discogs_dump(fixture, cache)
    return cache


def _fake_track(artist: str, title: str) -> object:
    return type("TrackStub", (), {"artist": artist, "title": title})()


def test_provider_returns_canonical_candidates_for_known_release(tmp_path: Path) -> None:
    cache = _seed_cache(tmp_path)
    provider = DiscogsProvider(cache_path=cache)

    candidates = provider.fetch(_fake_track("CamelPhat", "Cola"))

    canonical = {c.canonical_genre for c in candidates}
    assert "Tech House" in canonical
    assert "Deep House" in canonical
    assert all(c.source == "discogs" for c in candidates)
    assert all(0.0 <= c.confidence <= 1.0 for c in candidates)


def test_provider_normalizes_lookup_keys(tmp_path: Path) -> None:
    cache = _seed_cache(tmp_path)
    provider = DiscogsProvider(cache_path=cache)

    candidates = provider.fetch(_fake_track("  camelphat ", "  COLA  "))

    assert {c.canonical_genre for c in candidates} >= {"Tech House", "Deep House"}


def test_provider_returns_empty_for_unknown_track(tmp_path: Path) -> None:
    cache = _seed_cache(tmp_path)
    provider = DiscogsProvider(cache_path=cache)

    candidates = provider.fetch(_fake_track("Nobody", "Nothing"))

    assert candidates == []


def test_provider_confidence_reflects_style_agreement(tmp_path: Path) -> None:
    """Multiple releases for the same artist+title that agree on a style
    yield higher confidence than releases that disagree (Scenario 3.1)."""
    agreement_xml = """<?xml version="1.0" encoding="UTF-8"?>
<discogs>
  <releases>
    <release id="1">
      <artists><artist><name>DJ X</name></artist></artists>
      <title>Same</title>
      <styles><style>Tech House</style></styles>
    </release>
    <release id="2">
      <artists><artist><name>DJ X</name></artist></artists>
      <title>Same</title>
      <styles><style>Tech House</style></styles>
    </release>
    <release id="3">
      <artists><artist><name>DJ Y</name></artist></artists>
      <title>Conflict</title>
      <styles><style>Tech House</style></styles>
    </release>
    <release id="4">
      <artists><artist><name>DJ Y</name></artist></artists>
      <title>Conflict</title>
      <styles><style>Progressive House</style></styles>
    </release>
  </releases>
</discogs>
"""
    fixture = tmp_path / "discogs.xml"
    fixture.write_text(agreement_xml, encoding="utf-8")
    cache = tmp_path / "cache.sqlite"
    ingest_discogs_dump(fixture, cache)
    provider = DiscogsProvider(cache_path=cache)

    agreed = provider.fetch(_fake_track("DJ X", "Same"))
    conflicted = provider.fetch(_fake_track("DJ Y", "Conflict"))

    assert agreed and conflicted
    agreed_tech = next(c for c in agreed if c.canonical_genre == "Tech House")
    conflicted_tech = next(c for c in conflicted if c.canonical_genre == "Tech House")
    assert agreed_tech.confidence > conflicted_tech.confidence


def test_provider_name_is_discogs(tmp_path: Path) -> None:
    cache = _seed_cache(tmp_path)
    provider = DiscogsProvider(cache_path=cache)

    assert provider.name == "discogs"


def test_provider_does_not_mutate_track(tmp_path: Path) -> None:
    cache = _seed_cache(tmp_path)
    provider = DiscogsProvider(cache_path=cache)

    track = _fake_track("CamelPhat", "Cola")

    provider.fetch(track)  # repeated to ensure no in-place mutation
    provider.fetch(track)

    # The stub has no setters, but the assertion is that the provider never
    # touches the track object's attributes. A typed object with __slots__
    # would raise on assignment; we rely on the read-only contract.
    assert track.artist == "CamelPhat"
    assert track.title == "Cola"


def test_provider_satisfies_protocol(tmp_path: Path) -> None:
    from xfinaudio.genre.providers.base import GenreProvider

    provider = DiscogsProvider(cache_path=_seed_cache(tmp_path))

    assert isinstance(provider, GenreProvider)
