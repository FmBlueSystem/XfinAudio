import json
import sqlite3

import pytest

from xfinaudio.audio.spectral_profile import CURRENT_ANALYSIS_VERSION, SpectralProfile
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.track_repository import (
    SCHEMA_VERSION,
    DatabaseSchemaError,
    TrackRepository,
    UnsupportedDatabaseVersionError,
)


def test_track_repository_persists_and_round_trips_scan_records(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    repository = TrackRepository(db_path)
    original = TrackRecord(
        path="/music/track.flac",
        title="Track One",
        artist="Artist One",
        bpm=116.0,
        camelot_key="11B",
        energy_level=7,
        genre="Disco",
        tags=["Disco", "Classic"],
        metadata_status="complete",
        missing_required_fields=[],
        source_fields={"bpm": "bpm", "camelot_key": "key", "energy_level": "energy"},
        raw_metadata={"title": ["Track One"], "bpm": ["116.0"]},
    )

    repository.save_scan_results([original])

    assert repository.list_tracks() == [original]


def test_track_repository_replaces_existing_record_for_same_path(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    repository = TrackRepository(db_path)
    first = TrackRecord(path="/music/track.flac", title="Old", metadata_status="incomplete")
    second = TrackRecord(path="/music/track.flac", title="New", metadata_status="complete", bpm=120.0)

    repository.save_scan_results([first])
    repository.save_scan_results([second])

    assert repository.list_tracks() == [second]


def test_track_repository_initializes_schema_user_version(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"

    TrackRepository(db_path)

    with sqlite3.connect(db_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION


def test_track_repository_rejects_future_schema_without_resetting_version(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    future_version = SCHEMA_VERSION + 1
    with sqlite3.connect(db_path) as connection:
        connection.execute(f"PRAGMA user_version = {future_version}")

    with pytest.raises(UnsupportedDatabaseVersionError, match="Unsupported database schema version"):
        TrackRepository(db_path)

    with sqlite3.connect(db_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == future_version


def test_track_repository_accepts_current_schema_version(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    TrackRepository(db_path)

    repository = TrackRepository(db_path)

    assert repository.list_tracks() == []


def test_track_repository_rejects_unversioned_partial_tracks_table_without_marking_v1(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE tracks (path TEXT PRIMARY KEY, title TEXT)")
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0

    with pytest.raises(DatabaseSchemaError, match="Unversioned database contains an existing tracks table"):
        TrackRepository(db_path)

    with sqlite3.connect(db_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0


def test_track_repository_list_display_tracks_omits_large_raw_metadata_for_ui(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    repository = TrackRepository(db_path)
    original = TrackRecord(
        path="/music/track.flac",
        title="Track One",
        artist="Artist One",
        bpm=116.0,
        camelot_key="11B",
        energy_level=7,
        genre="Disco",
        tags=["Disco", "Classic"],
        metadata_status="complete",
        missing_required_fields=[],
        source_fields={"bpm": "bpm"},
        raw_metadata={"huge": ["payload"]},
    )

    repository.save_scan_results([original])

    display_records = repository.list_display_tracks()

    assert display_records == [
        TrackRecord(
            path="/music/track.flac",
            title="Track One",
            artist="Artist One",
            bpm=116.0,
            camelot_key="11B",
            energy_level=7,
            genre="Disco",
            tags=["Disco", "Classic"],
            metadata_status="complete",
            missing_required_fields=[],
        )
    ]


def test_track_repository_creates_index_on_metadata_status(tmp_path) -> None:
    import sqlite3

    db_path = tmp_path / "xfinaudio.sqlite3"
    TrackRepository(db_path)

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_tracks_metadata_status'"
        ).fetchone()

    assert row is not None, "idx_tracks_metadata_status index should be created on initialization"


def test_track_repository_round_trips_spectral_profile(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    repository = TrackRepository(db_path)
    profile = SpectralProfile(
        red_ratio=0.1,
        green_ratio=0.8,
        blue_ratio=0.1,
        centroid_hz=500.0,
        rolloff_hz=1200.0,
        rms=0.05,
        dominant_color="GREEN",
    )
    original = TrackRecord(
        path="/music/track.flac",
        title="Track One",
        metadata_status="complete",
        spectral_profile=profile,
    )

    repository.save_scan_results([original])

    assert repository.list_tracks() == [original]


@pytest.mark.parametrize("stored_color", ["RED", None, "NOT_A_COLOR"])
def test_track_repository_recomputes_dominant_color_on_read(tmp_path, stored_color: str | None) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    repository = TrackRepository(db_path)
    repository.save_scan_results([TrackRecord(path="/music/track.flac")])
    payload: dict[str, object] = {
        "red_ratio": 0.40,
        "green_ratio": 0.35,
        "blue_ratio": 0.25,
        "centroid_hz": 500.0,
        "rolloff_hz": 1200.0,
        "rms": 0.05,
    }
    if stored_color is not None:
        payload["dominant_color"] = stored_color
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE tracks SET spectral_profile_json = ? WHERE path = ?",
            (json.dumps(payload), "/music/track.flac"),
        )

    profile = repository.list_tracks()[0].spectral_profile

    assert profile is not None
    assert profile.dominant_color == "BLUE"


def test_track_repository_rejects_invalid_profile_ratios_on_read(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    repository = TrackRepository(db_path)
    repository.save_scan_results([TrackRecord(path="/music/track.flac")])
    payload = {
        "red_ratio": 1.1,
        "green_ratio": 0.0,
        "blue_ratio": 0.0,
        "dominant_color": "RED",
    }
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE tracks SET spectral_profile_json = ? WHERE path = ?",
            (json.dumps(payload), "/music/track.flac"),
        )

    assert repository.list_tracks()[0].spectral_profile is None


def test_track_repository_migrates_v1_database_to_v3(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE tracks (
                path TEXT PRIMARY KEY,
                title TEXT,
                artist TEXT,
                bpm REAL,
                camelot_key TEXT,
                energy_level INTEGER,
                duration REAL,
                genre TEXT,
                tags_json TEXT NOT NULL DEFAULT '[]',
                metadata_status TEXT NOT NULL CHECK(metadata_status IN ('complete', 'incomplete')),
                missing_required_fields_json TEXT NOT NULL DEFAULT '[]',
                source_fields_json TEXT NOT NULL DEFAULT '{}',
                raw_metadata_json TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        connection.execute("PRAGMA user_version = 1")

    repository = TrackRepository(db_path)

    with sqlite3.connect(db_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
    assert repository.list_tracks() == []


def test_track_repository_list_display_tracks_includes_spectral_profile(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    repository = TrackRepository(db_path)
    profile = SpectralProfile(
        red_ratio=0.9,
        green_ratio=0.05,
        blue_ratio=0.05,
        dominant_color="RED",
    )
    original = TrackRecord(
        path="/music/track.flac",
        title="Track One",
        metadata_status="complete",
        spectral_profile=profile,
        raw_metadata={"huge": ["payload"]},
    )

    repository.save_scan_results([original])

    display_records = repository.list_display_tracks()

    assert len(display_records) == 1
    assert display_records[0].spectral_profile == profile
    assert display_records[0].raw_metadata == {}


def test_track_repository_load_spectral_profile_cache_returns_profiles_with_identity(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    repository = TrackRepository(db_path)
    audio_file = tmp_path / "track.flac"
    audio_file.write_text("dummy audio content")
    profile = SpectralProfile(
        red_ratio=0.9,
        green_ratio=0.05,
        blue_ratio=0.05,
        dominant_color="RED",
        analysis_version=CURRENT_ANALYSIS_VERSION,
    )
    record = TrackRecord(
        path=str(audio_file),
        title="Track One",
        metadata_status="complete",
        spectral_profile=profile,
    )

    repository.save_scan_results([record])
    cache = repository.load_spectral_profile_cache([str(audio_file)])

    stat = audio_file.stat()
    assert cache == {str(audio_file): (stat.st_mtime_ns, stat.st_size, profile)}


@pytest.mark.parametrize("analysis_version", [1, CURRENT_ANALYSIS_VERSION + 1])
def test_track_repository_cache_excludes_non_current_profiles(tmp_path, analysis_version: int) -> None:
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    audio_file = tmp_path / "track.flac"
    audio_file.write_text("audio")
    profile = SpectralProfile(
        red_ratio=0.9,
        green_ratio=0.05,
        blue_ratio=0.05,
        dominant_color="RED",
        analysis_version=analysis_version,
    )
    repository.save_scan_results([TrackRecord(path=str(audio_file), spectral_profile=profile)])

    assert repository.load_spectral_profile_cache([str(audio_file)]) == {}
    assert repository.list_tracks()[0].spectral_profile == profile


def test_track_repository_deserializes_legacy_profile_as_version_one(tmp_path) -> None:
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    repository.save_scan_results([TrackRecord(path="/music/legacy.flac")])
    payload = {
        "red_ratio": 0.9,
        "green_ratio": 0.05,
        "blue_ratio": 0.05,
        "dominant_color": "RED",
    }
    with sqlite3.connect(repository.db_path) as connection:
        connection.execute(
            "UPDATE tracks SET spectral_profile_json = ? WHERE path = ?",
            (json.dumps(payload), "/music/legacy.flac"),
        )

    profile = repository.list_tracks()[0].spectral_profile

    assert profile is not None
    assert profile.analysis_version == 1


def test_save_scan_results_preserves_profile_when_file_identity_matches(tmp_path) -> None:
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    audio_file = tmp_path / "track.flac"
    audio_file.write_text("unchanged")
    profile = SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")
    repository.save_scan_results([TrackRecord(path=str(audio_file), title="Old", spectral_profile=profile)])

    repository.save_scan_results([TrackRecord(path=str(audio_file), title="Refreshed")])

    restored = repository.list_tracks()[0]
    assert restored.title == "Refreshed"
    assert restored.spectral_profile == profile


def test_save_scan_results_drops_profile_when_file_identity_changes(tmp_path) -> None:
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    audio_file = tmp_path / "track.flac"
    audio_file.write_text("before")
    profile = SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")
    repository.save_scan_results([TrackRecord(path=str(audio_file), spectral_profile=profile)])
    audio_file.write_text("after with changed size")

    repository.save_scan_results([TrackRecord(path=str(audio_file))])

    assert repository.list_tracks()[0].spectral_profile is None


def test_track_repository_load_spectral_profile_cache_returns_empty_for_missing_file(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    repository = TrackRepository(db_path)

    cache = repository.load_spectral_profile_cache(["/nonexistent/track.flac"])

    assert cache == {}
