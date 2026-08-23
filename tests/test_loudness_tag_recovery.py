from __future__ import annotations

from pathlib import Path

import pytest

from xfinaudio.audio.loudness_tags import recover_loudness_profile
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import scan_folder
from xfinaudio.library.track_repository import TrackRepository

_PAYLOAD = "lufs=-9.8;lra=4.2;dbtp=-0.7;v=1;engine=ffmpeg-test"


@pytest.mark.parametrize(
    ("suffix", "key", "supported"),
    [
        (".mp3", "TXXX:XFINAUDIO_LOUDNESS", True),
        (".flac", "XFINAUDIO_LOUDNESS", True),
        (".wav", "TXXX:XFINAUDIO_LOUDNESS", True),
        (".aiff", "TXXX:XFINAUDIO_LOUDNESS", True),
        (".m4a", "TXXX:XFINAUDIO_LOUDNESS", False),
        (".ogg", "XFINAUDIO_LOUDNESS", False),
    ],
)
def test_recovery_capability_map_stamps_current_identity(
    tmp_path: Path, suffix: str, key: str, supported: bool
) -> None:
    path = tmp_path / f"track{suffix}"
    path.write_text("audio")

    profile = recover_loudness_profile(path, {key: [_PAYLOAD]}, audio_md5="flac-md5")

    assert (profile is not None) is supported
    if profile is not None:
        assert (profile.lufs_integrated, profile.loudness_range_lra, profile.true_peak_dbtp) == (-9.8, 4.2, -0.7)
        assert (profile.source_mtime_ns, profile.source_size_bytes) == (path.stat().st_mtime_ns, path.stat().st_size)
        assert profile.source_audio_md5 == ("flac-md5" if suffix == ".flac" else None)


@pytest.mark.parametrize(
    "tags",
    [
        {"XFINAUDIO_LOUDNESS": ["lufs=-9.8;lra=4.2;dbtp=-0.7;v=2;engine=ffmpeg-test"]},
        {"XFINAUDIO_LOUDNESS": ["lufs=bad;lra=4.2;dbtp=-0.7;v=1;engine=ffmpeg-test"]},
        {"COMMENT": [_PAYLOAD]},
        {"REPLAYGAIN_TRACK_GAIN": ["-8.0 LUFS"]},
    ],
)
def test_recovery_rejects_malformed_foreign_and_comment_values(tmp_path: Path, tags: dict[str, list[str]]) -> None:
    path = tmp_path / "track.flac"
    path.write_text("audio")

    assert recover_loudness_profile(path, tags) is None


def test_scan_recovers_ephemeral_profile_without_retaining_structured_raw_tag(tmp_path: Path) -> None:
    path = tmp_path / "track.flac"
    path.write_text("audio")

    records = scan_folder(
        tmp_path,
        list_paths=lambda _: [path],
        read_tags=lambda _: {"XFINAUDIO_LOUDNESS": [_PAYLOAD], "__audio_md5__": "flac-md5"},
        resolve_spectral_profiles=False,
    )

    assert records[0].loudness_profile is not None
    assert records[0].loudness_profile.source_audio_md5 == "flac-md5"
    assert "XFINAUDIO_LOUDNESS" not in records[0].raw_metadata


def test_recovered_profile_populates_absent_database_row_but_never_replaces_existing(tmp_path: Path) -> None:
    path = tmp_path / "track.flac"
    path.write_text("audio")
    recovered = recover_loudness_profile(path, {"XFINAUDIO_LOUDNESS": [_PAYLOAD]})
    assert recovered is not None
    repository = TrackRepository(tmp_path / "library.sqlite3")

    repository.save_scan_results([TrackRecord(path=str(path), loudness_profile=recovered)])
    assert repository.list_tracks()[0].loudness_profile == recovered
    existing = recovered.model_copy(update={"lufs_integrated": -7.0, "engine_fingerprint": "ffmpeg-db"})
    repository.update_loudness_profile(str(path), existing)
    repository.save_scan_results([TrackRecord(path=str(path), loudness_profile=recovered)])

    assert repository.list_tracks()[0].loudness_profile == existing


def test_malformed_recovery_tag_never_fails_scan(tmp_path: Path) -> None:
    path = tmp_path / "track.flac"
    path.write_text("audio")

    records = scan_folder(
        tmp_path,
        list_paths=lambda _: [path],
        read_tags=lambda _: {"XFINAUDIO_LOUDNESS": ["not a payload"]},
        resolve_spectral_profiles=False,
    )

    assert records[0].loudness_profile is None
