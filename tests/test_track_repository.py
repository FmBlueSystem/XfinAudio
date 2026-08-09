import json
import os
import sqlite3

import pytest

from xfinaudio.audio.danceability import CURRENT_DANCEABILITY_VERSION, DanceabilityProfile
from xfinaudio.audio.spectral_profile import (
    CURRENT_ANALYSIS_VERSION,
    CURRENT_EDGE_ANALYSIS_VERSION,
    EdgeSpectralProfile,
    SpectralProfile,
)
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


def test_track_repository_round_trips_energy_curve_for_full_and_display_reads(tmp_path) -> None:
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    original = TrackRecord(
        path="/music/curve.flac",
        energy_level=7,
        energy_in=4,
        energy_out=8,
        energy_peak=9,
    )

    repository.save_scan_results([original])

    assert repository.list_tracks()[0].energy_in == 4
    assert repository.list_tracks()[0].energy_out == 8
    assert repository.list_tracks()[0].energy_peak == 9
    assert repository.list_display_tracks()[0].energy_in == 4
    assert repository.list_display_tracks()[0].energy_out == 8
    assert repository.list_display_tracks()[0].energy_peak == 9


def test_track_repository_round_trips_audio_md5_for_full_and_display_reads(tmp_path) -> None:
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    checksum = "0123456789abcdef0123456789abcdef"
    original = TrackRecord(path="/music/track.flac", title="Track One", audio_md5=checksum)

    repository.save_scan_results([original])

    assert repository.list_tracks()[0].audio_md5 == checksum
    assert repository.list_display_tracks()[0].audio_md5 == checksum


def test_track_repository_replaces_existing_record_for_same_path(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    repository = TrackRepository(db_path)
    first = TrackRecord(path="/music/track.flac", title="Old", metadata_status="incomplete")
    second = TrackRecord(path="/music/track.flac", title="New", metadata_status="complete", bpm=120.0)

    repository.save_scan_results([first])
    repository.save_scan_results([second])

    assert repository.list_tracks() == [second]


def test_track_repository_trims_legacy_raw_metadata_blobs_on_upgrade(tmp_path) -> None:
    """Databases written before the tag allowlist must be purged of unread blobs.

    A real 10,392-track library carried 261 MB of beatgrid/serato_overview/lyrics
    payload in raw_metadata_json that no code path ever reads.
    """
    db_path = tmp_path / "xfinaudio.sqlite3"
    repository = TrackRepository(db_path)
    repository.save_scan_results(
        [
            TrackRecord(
                path="/music/track.flac",
                title="Track One",
                metadata_status="incomplete",
                raw_metadata={
                    "title": ["Track One"],
                    "bpm": ["116.0"],
                    "beatgrid": "A" * 50_000,
                    "serato_overview": "B" * 20_000,
                    "lyrics": "C" * 10_000,
                },
            )
        ]
    )
    # Simulate a database written by the previous schema version.
    with sqlite3.connect(db_path) as connection:
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION - 1}")

    TrackRepository(db_path)

    with sqlite3.connect(db_path) as connection:
        stored = json.loads(connection.execute("SELECT raw_metadata_json FROM tracks").fetchone()[0])
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    assert stored == {"title": ["Track One"], "bpm": ["116.0"]}


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


def test_track_repository_migrates_v1_database_to_current_schema(tmp_path) -> None:
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
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    assert repository.list_tracks() == []


def test_track_repository_adds_nullable_energy_curve_columns_to_existing_schema(tmp_path) -> None:
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
                raw_metadata_json TEXT NOT NULL DEFAULT '{}',
                spectral_profile_json TEXT,
                file_mtime_ns INTEGER,
                file_size_bytes INTEGER
            )
            """
        )
        connection.execute(
            "INSERT INTO tracks (path, metadata_status) VALUES (?, ?)",
            ("/music/old.flac", "incomplete"),
        )
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    repository = TrackRepository(db_path)

    record = repository.list_tracks()[0]
    assert (record.energy_in, record.energy_out, record.energy_peak) == (None, None, None)
    with sqlite3.connect(db_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(tracks)")}
    assert {"energy_in", "energy_out", "energy_peak"} <= columns


def test_track_repository_adds_audio_md5_column_to_existing_schema(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    TrackRepository(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute("ALTER TABLE tracks RENAME TO tracks_old")
        connection.execute(
            """
            CREATE TABLE tracks AS
            SELECT path, title, artist, bpm, camelot_key, energy_level,
                   energy_in, energy_out, energy_peak, duration, genre, tags_json,
                   metadata_status, missing_required_fields_json, source_fields_json,
                   raw_metadata_json, spectral_profile_json, danceability_profile_json,
                   file_mtime_ns, file_size_bytes
            FROM tracks_old
            """
        )
        connection.execute("DROP TABLE tracks_old")
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    TrackRepository(db_path)

    with sqlite3.connect(db_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(tracks)")}
    assert "audio_md5" in columns


def test_save_scan_results_overwrites_derived_energy_curve_on_rescan(tmp_path) -> None:
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    repository.save_scan_results([TrackRecord(path="/music/curve.flac", energy_in=4, energy_out=8, energy_peak=9)])

    repository.save_scan_results([TrackRecord(path="/music/curve.flac", energy_in=2, energy_out=3, energy_peak=5)])

    record = repository.list_tracks()[0]
    assert (record.energy_in, record.energy_out, record.energy_peak) == (2, 3, 5)


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


def test_track_repository_load_spectral_profile_cache_exceeding_sqlite_variable_limit(tmp_path) -> None:
    """A library larger than SQLITE_MAX_VARIABLE_NUMBER (32766) must still load.

    A single IN (?,?,...) with one placeholder per path raises OperationalError
    past that limit, and the caller swallows it, so spectral analysis would die
    silently on large libraries.
    """
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    audio_file = tmp_path / "track.flac"
    audio_file.write_text("dummy audio content")
    profile = SpectralProfile(
        red_ratio=0.9,
        green_ratio=0.05,
        blue_ratio=0.05,
        dominant_color="RED",
        analysis_version=CURRENT_ANALYSIS_VERSION,
    )
    repository.save_scan_results(
        [TrackRecord(path=str(audio_file), title="Track One", metadata_status="complete", spectral_profile=profile)]
    )
    paths = [str(audio_file)] + [f"/music/absent{index}.flac" for index in range(40_000)]

    cache = repository.load_spectral_profile_cache(paths)

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


def test_save_scan_results_preserves_expensive_profiles_when_audio_md5_matches_despite_mtime_change(tmp_path) -> None:
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    audio_file = tmp_path / "retagged.flac"
    audio_file.write_text("unchanged audio")
    checksum = "0123456789abcdef0123456789abcdef"
    spectral = SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")
    danceability = _danceability_profile()
    repository.save_scan_results(
        [
            TrackRecord(
                path=str(audio_file),
                title="Old",
                audio_md5=checksum,
                spectral_profile=spectral,
                danceability_profile=danceability,
            )
        ]
    )
    stat = audio_file.stat()
    os.utime(audio_file, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1))

    repository.save_scan_results([TrackRecord(path=str(audio_file), title="Refreshed", audio_md5=checksum)])

    restored = repository.list_tracks()[0]
    assert restored.title == "Refreshed"
    assert restored.spectral_profile == spectral
    assert restored.danceability_profile == danceability


def test_save_scan_results_drops_expensive_profiles_when_audio_md5_and_fallback_identity_change(tmp_path) -> None:
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    audio_file = tmp_path / "changed.flac"
    audio_file.write_text("same size bytes")
    spectral = SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")
    danceability = _danceability_profile()
    repository.save_scan_results(
        [
            TrackRecord(
                path=str(audio_file),
                audio_md5="0123456789abcdef0123456789abcdef",
                spectral_profile=spectral,
                danceability_profile=danceability,
            )
        ]
    )
    stat = audio_file.stat()
    os.utime(audio_file, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1))

    repository.save_scan_results([TrackRecord(path=str(audio_file), audio_md5="fedcba9876543210fedcba9876543210")])

    restored = repository.list_tracks()[0]
    assert restored.spectral_profile is None
    assert restored.danceability_profile is None


@pytest.mark.parametrize(
    ("stored_audio_md5", "incoming_audio_md5"),
    [(None, "0123456789abcdef0123456789abcdef"), ("0123456789abcdef0123456789abcdef", None)],
)
@pytest.mark.parametrize("fallback_identity_matches", [True, False])
def test_save_scan_results_uses_mtime_size_fallback_when_either_audio_md5_is_missing(
    tmp_path,
    stored_audio_md5: str | None,
    incoming_audio_md5: str | None,
    fallback_identity_matches: bool,
) -> None:
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    audio_file = tmp_path / "fallback.flac"
    audio_file.write_text("unchanged audio")
    spectral = SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")
    danceability = _danceability_profile()
    repository.save_scan_results(
        [
            TrackRecord(
                path=str(audio_file),
                audio_md5=stored_audio_md5,
                spectral_profile=spectral,
                danceability_profile=danceability,
            )
        ]
    )
    if not fallback_identity_matches:
        stat = audio_file.stat()
        os.utime(audio_file, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1))

    repository.save_scan_results([TrackRecord(path=str(audio_file), audio_md5=incoming_audio_md5)])

    restored = repository.list_tracks()[0]
    expected_spectral = spectral if fallback_identity_matches else None
    expected_danceability = danceability if fallback_identity_matches else None
    assert restored.spectral_profile == expected_spectral
    assert restored.danceability_profile == expected_danceability


def test_save_scan_results_prefers_incoming_expensive_profiles_over_preserved_values(tmp_path) -> None:
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    audio_file = tmp_path / "reanalyzed.flac"
    audio_file.write_text("audio")
    old_spectral = SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")
    new_spectral = SpectralProfile(red_ratio=0.05, green_ratio=0.9, blue_ratio=0.05, dominant_color="GREEN")
    old_danceability = _danceability_profile()
    new_danceability = DanceabilityProfile(
        score=0.91,
        pulse_clarity=0.92,
        tempo_confidence=0.93,
        percussive_ratio=0.94,
    )
    repository.save_scan_results(
        [
            TrackRecord(
                path=str(audio_file),
                audio_md5="0123456789abcdef0123456789abcdef",
                spectral_profile=old_spectral,
                danceability_profile=old_danceability,
            )
        ]
    )

    repository.save_scan_results(
        [
            TrackRecord(
                path=str(audio_file),
                audio_md5="fedcba9876543210fedcba9876543210",
                spectral_profile=new_spectral,
                danceability_profile=new_danceability,
            )
        ]
    )

    restored = repository.list_tracks()[0]
    assert restored.spectral_profile == new_spectral
    assert restored.danceability_profile == new_danceability


def test_track_repository_load_spectral_profile_cache_returns_empty_for_missing_file(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    repository = TrackRepository(db_path)

    cache = repository.load_spectral_profile_cache(["/nonexistent/track.flac"])

    assert cache == {}


def _danceability_profile(*, analysis_version: int = CURRENT_DANCEABILITY_VERSION) -> DanceabilityProfile:
    return DanceabilityProfile(
        score=0.72,
        pulse_clarity=0.8,
        tempo_confidence=0.9,
        percussive_ratio=0.6,
        analysis_version=analysis_version,
    )


def _edge_spectral_profile(*, analysis_version: int = CURRENT_EDGE_ANALYSIS_VERSION) -> EdgeSpectralProfile:
    return EdgeSpectralProfile(
        intro=SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED"),
        outro=SpectralProfile(red_ratio=0.05, green_ratio=0.05, blue_ratio=0.9, dominant_color="BLUE"),
        analysis_version=analysis_version,
    )


def test_track_repository_round_trips_danceability_profile_for_full_and_display_reads(tmp_path) -> None:
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    profile = _danceability_profile()
    original = TrackRecord(
        path="/music/track.flac",
        title="Track One",
        metadata_status="complete",
        danceability_profile=profile,
    )

    repository.save_scan_results([original])

    assert repository.list_tracks()[0].danceability_profile == profile
    assert repository.list_display_tracks()[0].danceability_profile == profile


def test_track_repository_tolerates_corrupt_danceability_profile_json(tmp_path) -> None:
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    repository.save_scan_results([TrackRecord(path="/music/track.flac")])
    with sqlite3.connect(repository.db_path) as connection:
        connection.execute(
            "UPDATE tracks SET danceability_profile_json = ? WHERE path = ?",
            ("not-json", "/music/track.flac"),
        )

    assert repository.list_tracks()[0].danceability_profile is None


def test_save_scan_results_preserves_danceability_profile_when_file_identity_matches(tmp_path) -> None:
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    audio_file = tmp_path / "track.flac"
    audio_file.write_text("unchanged")
    profile = _danceability_profile()
    repository.save_scan_results([TrackRecord(path=str(audio_file), title="Old", danceability_profile=profile)])

    repository.save_scan_results([TrackRecord(path=str(audio_file), title="Refreshed")])

    restored = repository.list_tracks()[0]
    assert restored.title == "Refreshed"
    assert restored.danceability_profile == profile


def test_save_scan_results_drops_danceability_profile_when_file_identity_changes(tmp_path) -> None:
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    audio_file = tmp_path / "track.flac"
    audio_file.write_text("before")
    profile = _danceability_profile()
    repository.save_scan_results([TrackRecord(path=str(audio_file), danceability_profile=profile)])
    audio_file.write_text("after with changed size")

    repository.save_scan_results([TrackRecord(path=str(audio_file))])

    assert repository.list_tracks()[0].danceability_profile is None


def test_update_danceability_profile_returns_whether_path_exists(tmp_path) -> None:
    audio_file = tmp_path / "track.flac"
    audio_file.write_text("audio")
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    repository.save_scan_results([TrackRecord(path=str(audio_file))])
    profile = _danceability_profile()

    assert repository.update_danceability_profile(str(audio_file), profile) is True
    assert repository.update_danceability_profile("/music/missing.flac", profile) is False
    assert repository.list_tracks()[0].danceability_profile == profile


def test_load_danceability_profile_cache_returns_current_profiles_with_identity(tmp_path) -> None:
    audio_file = tmp_path / "track.flac"
    audio_file.write_text("audio")
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    profile = _danceability_profile()
    repository.save_scan_results([TrackRecord(path=str(audio_file), danceability_profile=profile)])

    cache = repository.load_danceability_profile_cache([str(audio_file), "/music/missing.flac"])

    stat = audio_file.stat()
    assert cache == {str(audio_file): (stat.st_mtime_ns, stat.st_size, profile)}


@pytest.mark.parametrize(
    "analysis_version",
    [CURRENT_DANCEABILITY_VERSION + 1, CURRENT_DANCEABILITY_VERSION + 2],
)
def test_load_danceability_profile_cache_excludes_non_current_profiles(tmp_path, analysis_version: int) -> None:
    audio_file = tmp_path / "track.flac"
    audio_file.write_text("audio")
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    profile = _danceability_profile(analysis_version=analysis_version)
    repository.save_scan_results([TrackRecord(path=str(audio_file), danceability_profile=profile)])

    assert repository.load_danceability_profile_cache([str(audio_file)]) == {}
    assert repository.list_tracks()[0].danceability_profile == profile


def test_track_repository_adds_danceability_column_to_existing_schema(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    TrackRepository(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute("ALTER TABLE tracks RENAME TO tracks_old")
        connection.execute(
            """
            CREATE TABLE tracks AS
            SELECT path, title, artist, bpm, camelot_key, energy_level,
                   energy_in, energy_out, energy_peak, duration, genre, tags_json,
                   metadata_status, missing_required_fields_json, source_fields_json,
                   raw_metadata_json, spectral_profile_json, file_mtime_ns, file_size_bytes
            FROM tracks_old
            """
        )
        connection.execute("DROP TABLE tracks_old")
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    TrackRepository(db_path)

    with sqlite3.connect(db_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(tracks)")}
    assert "danceability_profile_json" in columns


def test_track_repository_round_trips_edge_profile_for_full_and_display_reads(tmp_path) -> None:
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    profile = _edge_spectral_profile()
    repository.save_scan_results([TrackRecord(path="/music/track.flac", edge_spectral_profile=profile)])

    assert repository.list_tracks()[0].edge_spectral_profile == profile
    assert repository.list_display_tracks()[0].edge_spectral_profile == profile


def test_track_repository_tolerates_corrupt_edge_profile_json(tmp_path) -> None:
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    repository.save_scan_results([TrackRecord(path="/music/track.flac")])
    with sqlite3.connect(repository.db_path) as connection:
        connection.execute(
            "UPDATE tracks SET edge_spectral_profile_json = ? WHERE path = ?",
            ("not-json", "/music/track.flac"),
        )

    assert repository.list_tracks()[0].edge_spectral_profile is None


def test_edge_profile_preservation_uses_checksum_then_mtime_size_fallback(tmp_path) -> None:
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    audio_file = tmp_path / "retagged.flac"
    audio_file.write_text("audio")
    profile = _edge_spectral_profile()
    checksum = "0123456789abcdef0123456789abcdef"
    repository.save_scan_results([TrackRecord(path=str(audio_file), audio_md5=checksum, edge_spectral_profile=profile)])
    stat = audio_file.stat()
    os.utime(audio_file, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1))

    repository.save_scan_results([TrackRecord(path=str(audio_file), audio_md5=checksum)])
    assert repository.list_tracks()[0].edge_spectral_profile == profile

    repository.save_scan_results([TrackRecord(path=str(audio_file), audio_md5=None)])
    assert repository.list_tracks()[0].edge_spectral_profile == profile

    stat = audio_file.stat()
    os.utime(audio_file, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1))
    repository.save_scan_results([TrackRecord(path=str(audio_file), audio_md5=None)])
    assert repository.list_tracks()[0].edge_spectral_profile is None


def test_save_scan_results_prefers_incoming_edge_profile(tmp_path) -> None:
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    path = "/music/track.flac"
    old = _edge_spectral_profile()
    new = EdgeSpectralProfile(intro=old.outro, outro=old.intro)
    repository.save_scan_results([TrackRecord(path=path, edge_spectral_profile=old)])

    repository.save_scan_results([TrackRecord(path=path, edge_spectral_profile=new)])

    assert repository.list_tracks()[0].edge_spectral_profile == new


def test_update_edge_profile_returns_whether_path_exists(tmp_path) -> None:
    audio_file = tmp_path / "track.flac"
    audio_file.write_text("audio")
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    repository.save_scan_results([TrackRecord(path=str(audio_file))])
    profile = _edge_spectral_profile()

    assert repository.update_edge_spectral_profile(str(audio_file), profile) is True
    assert repository.update_edge_spectral_profile("/music/missing.flac", profile) is False
    assert repository.list_tracks()[0].edge_spectral_profile == profile


def test_load_edge_profile_cache_filters_version_and_chunks_queries(tmp_path) -> None:
    audio_file = tmp_path / "track.flac"
    audio_file.write_text("audio")
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    current = _edge_spectral_profile()
    repository.save_scan_results([TrackRecord(path=str(audio_file), edge_spectral_profile=current)])
    paths = [f"/music/missing-{index}.flac" for index in range(901)] + [str(audio_file)]

    cache = repository.load_edge_spectral_profile_cache(paths)

    stat = audio_file.stat()
    assert cache == {str(audio_file): (stat.st_mtime_ns, stat.st_size, current)}

    stale = _edge_spectral_profile(analysis_version=CURRENT_EDGE_ANALYSIS_VERSION + 1)
    repository.save_scan_results([TrackRecord(path=str(audio_file), edge_spectral_profile=stale)])
    assert repository.load_edge_spectral_profile_cache([str(audio_file)]) == {}


def test_track_repository_adds_edge_profile_column_to_existing_schema(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    TrackRepository(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute("ALTER TABLE tracks RENAME TO tracks_old")
        connection.execute(
            """
            CREATE TABLE tracks AS
            SELECT path, title, artist, bpm, camelot_key, energy_level,
                   energy_in, energy_out, energy_peak, duration, genre, tags_json,
                   metadata_status, missing_required_fields_json, source_fields_json,
                   raw_metadata_json, audio_md5, spectral_profile_json,
                   danceability_profile_json, file_mtime_ns, file_size_bytes
            FROM tracks_old
            """
        )
        connection.execute("DROP TABLE tracks_old")
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    TrackRepository(db_path)

    with sqlite3.connect(db_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(tracks)")}
    assert "edge_spectral_profile_json" in columns
