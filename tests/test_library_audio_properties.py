"""Read-only stream facts survive the scanner, database and public boundary."""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from mutagen import File

from xfinaudio.headless.common import _public_track
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import scan_folder
from xfinaudio.library.track_repository import SCHEMA_VERSION, TrackRepository


@pytest.fixture(scope="module")
def audio_fixtures(tmp_path_factory):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("Generated six-format fixtures require FFmpeg")
    root = tmp_path_factory.mktemp("library-stream-fixtures")
    formats = [
        ("flac.flac", ["-c:a", "flac"], "FLAC", None),
        ("cbr.mp3", ["-c:a", "libmp3lame", "-b:a", "128k"], "MP3", None),
        ("vbr.mp3", ["-c:a", "libmp3lame", "-q:a", "2"], "MP3", None),
        ("pcm.wav", ["-c:a", "pcm_s16le"], "WAV", None),
        ("pcm.aiff", ["-c:a", "pcm_s16be"], "AIFF", None),
        ("aac.m4a", ["-c:a", "aac"], "MP4", "AAC LC"),
        ("alac.m4a", ["-c:a", "alac"], "MP4", "ALAC"),
    ]
    for name, codec, _, _ in formats:
        subprocess.run(
            [ffmpeg, "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", *codec, str(root / name)],
            check=True,
            capture_output=True,
        )
    return root, formats


def test_real_audio_properties_survive_scan_restart_and_dto_without_audio_writes(audio_fixtures, tmp_path):
    root, formats = audio_fixtures
    before = {p: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns) for p in root.iterdir()}
    records = scan_folder(root, resolve_spectral_profiles=False)
    assert len(records) == len(formats), "Readable untagged WAV and AIFF must not disappear"
    repository = TrackRepository(tmp_path / "tracks.db")
    repository.save_scan_results(records)
    reopened = TrackRepository(repository.db_path)
    for rows in (records, reopened.list_tracks(), reopened.list_display_tracks()):
        by_name = {Path(r.path).name: r for r in rows}
        for name, _, container, codec in formats:
            record = by_name[name]
            assert record.audio_format == container
            assert record.audio_codec == codec
            assert record.bitrate_kbps == pytest.approx(File(root / name).info.bitrate / 1000)
            expected_mode = "CBR" if name == "cbr.mp3" else "VBR" if name == "vbr.mp3" else None
            assert record.bitrate_mode == expected_mode
            public = _public_track(record)
            assert public["audioFormat"] == container
            assert public["audioCodec"] == codec
            assert public["bitrateKbps"] == record.bitrate_kbps
            assert public["bitrateMode"] == expected_mode
            assert record.metadata_status == "incomplete"
    assert before == {p: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns) for p in root.iterdir()}


def test_format_is_sniffed_not_guessed_from_extension(audio_fixtures, tmp_path):
    root, _ = audio_fixtures
    shutil.copy2(root / "flac.flac", tmp_path / "misleading.m4a")
    record = scan_folder(tmp_path, resolve_spectral_profiles=False)[0]
    assert record.audio_format == "FLAC"


@pytest.mark.parametrize("rate", [None, 0, -1, float("nan"), float("inf"), "128000", True])
def test_unverified_container_and_invalid_bitrate_remain_unavailable(monkeypatch, rate):
    monkeypatch.setattr(
        "xfinaudio.library.scan_service.MutagenFile",
        lambda *args, **kwargs: SimpleNamespace(tags={}, info=SimpleNamespace(length=1, bitrate=rate)),
    )
    record = scan_folder(
        Path("/fixture"), list_paths=lambda _: [Path("/fixture/test.mp3")], resolve_spectral_profiles=False
    )[0]
    assert record.audio_format is None
    assert record.bitrate_kbps is None
    assert _public_track(record)["audioFormat"] is None


def test_version_six_migration_keeps_old_rows_and_readiness_and_accepts_rescan(tmp_path):
    path = tmp_path / "tracks.db"
    original = TrackRecord(path="/fixture/existing.flac", title="Keep", metadata_status="complete")
    repository = TrackRepository(path)
    repository.save_scan_results([original])
    with sqlite3.connect(path) as db:
        for column in ("audio_format", "audio_codec", "bitrate_kbps", "bitrate_mode"):
            if column in {row[1] for row in db.execute("PRAGMA table_info(tracks)")}:
                db.execute(f"ALTER TABLE tracks DROP COLUMN {column}")
        db.execute("PRAGMA user_version=6")
    reopened = TrackRepository(path)
    assert SCHEMA_VERSION == 7
    record = reopened.list_display_tracks()[0]
    assert record.title == "Keep" and record.metadata_status == "complete"
    assert record.audio_format is None and record.bitrate_kbps is None
    updated = record.model_copy(update={"audio_format": "FLAC", "bitrate_kbps": 765.4})
    reopened.save_scan_results([updated])
    assert TrackRepository(path).list_tracks()[0].bitrate_kbps == 765.4
    reopened.save_scan_results([original])
    assert reopened.list_tracks()[0].bitrate_kbps is None, "Rescan must clear stale stream facts"


def test_copied_legacy_library_ordinary_rescan_populates_unchanged_audio(audio_fixtures, tmp_path):
    from xfinaudio.headless.backend import HeadlessBackend

    root, formats = audio_fixtures
    original = HeadlessBackend(tmp_path / "old-profile")
    original.execute("library.scan", {"root": str(root)})
    with sqlite3.connect(original.repository.db_path) as db:
        for column in ("audio_format", "audio_codec", "bitrate_kbps", "bitrate_mode"):
            db.execute(f"ALTER TABLE tracks DROP COLUMN {column}")
        db.execute("PRAGMA user_version=6")
    shutil.copytree(original.data_dir, tmp_path / "copied-profile")
    source_db_before = original.repository.db_path.read_bytes()
    audio_before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.iterdir()}
    copied = HeadlessBackend(tmp_path / "copied-profile")
    assert all(t["audioFormat"] is None for t in copied.execute("library.list", {})["tracks"])
    rescanned = copied.execute("library.rescan", {})
    assert len(rescanned["tracks"]) == len(formats)
    assert all(t["audioFormat"] and t["bitrateKbps"] > 0 for t in rescanned["tracks"])
    assert original.repository.db_path.read_bytes() == source_db_before
    assert audio_before == {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.iterdir()}


def test_failed_audio_columns_migration_rolls_back_schema_and_version(tmp_path, monkeypatch):
    source = TrackRepository(tmp_path / "old.db")
    source.save_scan_results([TrackRecord(path="/unchanged.flac", title="Kept")])
    with sqlite3.connect(source.db_path) as db:
        for column in ("audio_format", "audio_codec", "bitrate_kbps", "bitrate_mode"):
            db.execute(f"ALTER TABLE tracks DROP COLUMN {column}")
        db.execute("PRAGMA user_version=6")
    copied = tmp_path / "copy.db"
    shutil.copy2(source.db_path, copied)
    original_ensure = TrackRepository._ensure_schema

    def fail_after_alters(connection):
        original_ensure(connection)
        raise RuntimeError("Synthetic migration interruption")

    monkeypatch.setattr(TrackRepository, "_ensure_schema", staticmethod(fail_after_alters))
    with pytest.raises(RuntimeError, match="interruption"):
        TrackRepository(copied)
    with sqlite3.connect(copied) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 6
        assert "audio_format" not in {r[1] for r in db.execute("PRAGMA table_info(tracks)")}
        assert db.execute("SELECT title FROM tracks").fetchone()[0] == "Kept"
