"""Tests for the read-only library health analyzer."""

from __future__ import annotations

from xfinaudio.library.library_health import analyze_library_health
from xfinaudio.library.models import TrackRecord


def _track(
    path: str,
    *,
    bpm: float | None = 124.0,
    camelot_key: str | None = "8A",
    energy_level: int | None = 5,
    genre: str | None = "House",
    title: str | None = "Song",
    artist: str | None = "Artist",
    status: str = "complete",
) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=title,
        artist=artist,
        bpm=bpm,
        camelot_key=camelot_key,
        energy_level=energy_level,
        genre=genre,
        metadata_status=status,  # type: ignore[arg-type]
    )


def test_empty_library_is_fully_healthy() -> None:
    report = analyze_library_health([])
    assert report.total == 0
    assert report.health_score == 1.0


def test_counts_missing_fields() -> None:
    tracks = [
        _track("a"),
        _track("b", camelot_key=None, status="incomplete"),
        _track("c", bpm=None, status="incomplete"),
        _track("d", energy_level=None, status="incomplete"),
    ]
    report = analyze_library_health(tracks)
    assert report.total == 4
    assert report.missing_key == 1
    assert report.missing_bpm == 1
    assert report.missing_energy == 1


def test_flags_suspicious_bpm_out_of_dj_range() -> None:
    tracks = [
        _track("slow", bpm=48.0),  # too slow → likely half-time
        _track("fast", bpm=212.0),  # too fast → likely double-time
        _track("ok", bpm=128.0),
    ]
    report = analyze_library_health(tracks)
    assert report.suspicious_bpm == 2


def test_detects_genre_spelling_variants() -> None:
    tracks = [
        _track("a", genre="Hip-Hop"),
        _track("b", genre="Hip Hop"),
        _track("c", genre="hiphop"),
        _track("d", genre="House"),
    ]
    report = analyze_library_health(tracks)
    # Hip-Hop / Hip Hop / hiphop normalize to one bucket with 3 raw spellings.
    assert report.genre_variant_groups == 1


def test_health_score_reflects_clean_fraction() -> None:
    tracks = [
        _track("a"),  # clean
        _track("b"),  # clean
        _track("c", camelot_key=None, status="incomplete"),  # not clean
        _track("d", bpm=999.0),  # suspicious bpm → not clean
    ]
    report = analyze_library_health(tracks)
    assert report.health_score == 0.5  # 2 of 4 fully clean
