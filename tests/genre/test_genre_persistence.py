"""Tests for genre decision persistence (PR5 Task 5.3).

Covers spec Requirement 6 Scenarios 6.1-6.3.
"""

from __future__ import annotations

from pathlib import Path

from xfinaudio.genre.models import GenreCandidate, GenreDecision, GenreProvenance
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.track_repository import SCHEMA_VERSION, TrackRepository


def _decision() -> GenreDecision:
    candidate = GenreCandidate(
        canonical_genre="Tech House",
        raw_label="tech house",
        source="discogs",
        confidence=0.9,
    )
    return GenreDecision(
        primary="Tech House",
        top_n=("Tech House", "Deep House"),
        confidence=0.9,
        low_confidence=False,
        provenance=GenreProvenance(
            candidates=(candidate,),
            source_trust={"discogs": 1.0},
            scores={"Tech House": 0.9, "Deep House": 0.4},
        ),
    )


def test_genre_decision_round_trips_through_repository(tmp_path: Path) -> None:
    repo = TrackRepository(tmp_path / "library.sqlite")
    record = TrackRecord(
        path="/library/track.flac",
        title="Cola",
        artist="CamelPhat",
        genre="Electronica",
        genre_decision=_decision(),
    )

    repo.save_scan_results([record])
    loaded = repo.list_tracks()

    assert len(loaded) == 1
    assert loaded[0].genre == "Electronica"  # original tag preserved
    assert loaded[0].genre_decision is not None
    assert loaded[0].genre_decision.primary == "Tech House"
    assert loaded[0].genre_decision.top_n == ("Tech House", "Deep House")
    assert loaded[0].genre_decision.confidence == 0.9
    assert loaded[0].genre_decision.provenance.scores["Tech House"] == 0.9


def test_genre_decision_survives_app_restart(tmp_path: Path) -> None:
    db = tmp_path / "library.sqlite"
    record = TrackRecord(
        path="/library/track.flac",
        title="Cola",
        artist="CamelPhat",
        genre_decision=_decision(),
    )

    TrackRepository(db).save_scan_results([record])
    reloaded = TrackRepository(db).list_tracks()

    assert reloaded[0].genre_decision == record.genre_decision


def test_original_genre_tag_is_preserved_with_decision(tmp_path: Path) -> None:
    """Spec Scenario 6.2: original file-tag genre remains available and unchanged."""
    repo = TrackRepository(tmp_path / "library.sqlite")
    record = TrackRecord(
        path="/library/track.flac",
        genre="Electronica",
        genre_decision=_decision(),
    )

    repo.save_scan_results([record])
    loaded = repo.list_tracks()

    # Original raw genre survives
    assert loaded[0].genre == "Electronica"
    # And the canonical decision sits next to it
    assert loaded[0].genre_decision.primary == "Tech House"


def test_re_enrichment_replaces_decision(tmp_path: Path) -> None:
    """Spec Scenario 6.3: re-enrichment updates the decision in place."""
    repo = TrackRepository(tmp_path / "library.sqlite")
    first = TrackRecord(
        path="/library/track.flac",
        title="Track",
        genre_decision=_decision(),
    )
    second_decision = GenreDecision(
        primary="Techno",
        top_n=("Techno",),
        confidence=0.8,
        low_confidence=False,
        provenance=GenreProvenance(),
    )
    second = first.model_copy(update={"genre_decision": second_decision})

    repo.save_scan_results([first])
    repo.save_scan_results([second])
    loaded = repo.list_tracks()

    assert loaded[0].genre_decision == second_decision
    assert loaded[0].genre_decision.primary == "Techno"


def test_track_without_decision_persists_none(tmp_path: Path) -> None:
    repo = TrackRepository(tmp_path / "library.sqlite")
    record = TrackRecord(path="/library/track.flac", title="Track", genre="House")

    repo.save_scan_results([record])
    loaded = repo.list_tracks()

    assert loaded[0].genre_decision is None
    assert loaded[0].genre == "House"


def test_schema_version_bumped_to_include_genre_decision() -> None:
    """A user opening the DB with a future client must be told the version."""
    assert SCHEMA_VERSION >= 4


def test_migrates_existing_v3_database_adds_genre_decision_column(tmp_path: Path) -> None:
    """An existing v3 DB must accept a fresh TrackRepository and gain the column."""
    import sqlite3

    db = tmp_path / "library.sqlite"
    # Create a v3 schema with one track row.
    with sqlite3.connect(db) as conn:
        conn.execute("PRAGMA user_version = 3")
        conn.execute(
            """
            CREATE TABLE tracks (
                path TEXT PRIMARY KEY,
                title TEXT, artist TEXT, bpm REAL, camelot_key TEXT, energy_level INTEGER,
                duration REAL, genre TEXT,
                tags_json TEXT NOT NULL DEFAULT '[]',
                metadata_status TEXT NOT NULL,
                missing_required_fields_json TEXT NOT NULL DEFAULT '[]',
                source_fields_json TEXT NOT NULL DEFAULT '{}',
                raw_metadata_json TEXT NOT NULL DEFAULT '{}',
                spectral_profile_json TEXT,
                file_mtime_ns INTEGER,
                file_size_bytes INTEGER
            )
            """
        )
        conn.execute(
            "INSERT INTO tracks (path, title, genre, tags_json, metadata_status, "
            "missing_required_fields_json, source_fields_json, raw_metadata_json) "
            "VALUES (?, ?, ?, '[]', 'complete', '[]', '{}', '{}')",
            ("/library/old.flac", "Old", "House"),
        )

    # Opening with current code must migrate without error and add the column.
    repo = TrackRepository(db)
    loaded = repo.list_tracks()

    assert len(loaded) == 1
    assert loaded[0].title == "Old"
    assert loaded[0].genre == "House"
    assert loaded[0].genre_decision is None
