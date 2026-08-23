from __future__ import annotations

from pathlib import Path
from shutil import copyfile

import pytest
from mutagen.mp4 import MP4, AtomDataType, MP4FreeForm

from xfinaudio.audio.loudness import LoudnessProfile, LoudnessStatus
from xfinaudio.audio.loudness_tags import LoudnessTagWriteStatus, recover_loudness_profile, write_loudness_tags
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import scan_folder
from xfinaudio.library.track_repository import TrackRepository

_PAYLOAD = "lufs=-9.8;lra=4.2;dbtp=-0.7;v=1;engine=ffmpeg-test"
_M4A_LOUDNESS_KEY = "----:com.bluesystemio.xfinaudio:XFINAUDIO_LOUDNESS"


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


def test_m4a_scan_recovers_only_app_owned_utf8_freeform_atom(tmp_path: Path) -> None:
    fixture = Path(__file__).resolve().parent / "fixtures" / "loudness" / "synthetic_tone_1khz_aac.m4a"
    path = tmp_path / "track.m4a"
    copyfile(fixture, path)
    profile = LoudnessProfile(
        lufs_integrated=-9.8,
        loudness_range_lra=4.2,
        true_peak_dbtp=-0.7,
        status=LoudnessStatus.MEASURED,
        engine_fingerprint="ffmpeg-test",
    )
    assert write_loudness_tags(path, profile).status is LoudnessTagWriteStatus.CHANGED

    records = scan_folder(tmp_path, resolve_spectral_profiles=False)
    assert records[0].loudness_profile is not None
    assert records[0].loudness_profile.engine_fingerprint == "ffmpeg-test"

    audio = MP4(path)
    assert audio.tags is not None
    audio.tags[_M4A_LOUDNESS_KEY] = [MP4FreeForm(b"foreign", dataformat=AtomDataType.IMPLICIT)]
    audio.tags["©cmt"] = [_PAYLOAD]
    audio.save()
    assert recover_loudness_profile(path, {"©cmt": [_PAYLOAD]}) is None
    assert recover_loudness_profile(path, {_M4A_LOUDNESS_KEY: audio.tags[_M4A_LOUDNESS_KEY]}) is None
    assert recover_loudness_profile(path, {"----:com.example:XFINAUDIO_LOUDNESS": [_PAYLOAD]}) is None

    repository = TrackRepository(tmp_path / "library.sqlite3")
    repository.save_scan_results(records)
    existing = records[0].loudness_profile.model_copy(update={"engine_fingerprint": "ffmpeg-db"})
    repository.update_loudness_profile(records[0].path, existing)
    repository.save_scan_results(records)
    assert repository.list_tracks()[0].loudness_profile == existing


@pytest.mark.parametrize(
    "tags",
    [
        {
            "----:com.bluesystemio.xfinaudio:xfinaudio_loudness": [
                MP4FreeForm(_PAYLOAD.encode(), dataformat=AtomDataType.UTF8)
            ]
        },
        {_M4A_LOUDNESS_KEY: [MP4FreeForm(b"\xff", dataformat=AtomDataType.UTF8)]},
        {
            _M4A_LOUDNESS_KEY: [
                MP4FreeForm(_PAYLOAD.encode(), dataformat=AtomDataType.UTF8),
                MP4FreeForm(_PAYLOAD.encode(), dataformat=AtomDataType.UTF8),
            ]
        },
    ],
)
def test_m4a_recovery_rejects_case_variants_invalid_utf8_and_multiple_values(
    tmp_path: Path, tags: dict[str, list[MP4FreeForm]]
) -> None:
    path = tmp_path / "track.m4a"
    path.write_text("audio")

    assert recover_loudness_profile(path, tags) is None
