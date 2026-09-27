from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from shutil import copyfile
from typing import Any

import pytest
from mutagen.id3 import TXXX
from mutagen.mp4 import MP4, AtomDataType, MP4FreeForm

from xfinaudio.audio.loudness import LoudnessProfile, LoudnessStatus
from xfinaudio.audio.loudness_tags import LoudnessTagWriteStatus, recover_loudness_profile, write_loudness_tags
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import scan_folder
from xfinaudio.library.track_repository import TrackRepository

_PAYLOAD = "lufs=-9.8;lra=4.2;dbtp=-0.7;v=1;engine=ffmpeg-test"
_M4A_LOUDNESS_KEY = "----:com.bluesystemio.xfinaudio:XFINAUDIO_LOUDNESS"
_LOUDNESS_COMMENT = "-9.8 LUFS · 4.2 LRA · -0.7 dBTP"


@dataclass
class FakeAudio:
    tags: Any
    save_count: int = 0


def measured_profile(lufs: float = -9.8, lra: float = 4.2, dbtp: float = -0.7) -> LoudnessProfile:
    return LoudnessProfile(
        lufs_integrated=lufs,
        loudness_range_lra=lra,
        true_peak_dbtp=dbtp,
        status=LoudnessStatus.MEASURED,
        engine_fingerprint="ffmpeg-test",
    )


def save(audio: FakeAudio) -> None:
    audio.save_count += 1


@dataclass
class FakeID3Tags:
    frames: list[object] = field(default_factory=list)

    def getall(self, frame_id: str) -> list[object]:
        return [frame for frame in self.frames if getattr(frame, "FrameID", None) == frame_id]

    def delall(self, key: str) -> None:
        self.frames = [
            frame
            for frame in self.frames
            if getattr(frame, "HashKey", None) != key and getattr(frame, "FrameID", None) != key
        ]

    def add(self, frame: object) -> None:
        self.frames.append(frame)


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


def test_flac_empty_description_is_populated_with_the_loudness_comment() -> None:
    tags: dict[str, list[str]] = {"COMMENT": ["old note"]}
    audio = FakeAudio(tags)

    result = write_loudness_tags(
        Path("/library/track.flac"), measured_profile(), load_audio=lambda _: audio, save_audio=save
    )

    assert result.status is LoudnessTagWriteStatus.CHANGED
    assert tags["DESCRIPTION"] == [_LOUDNESS_COMMENT]


def test_flac_existing_description_is_appended_with_the_loudness_comment() -> None:
    tags: dict[str, list[str]] = {"COMMENT": ["old note"], "DESCRIPTION": ["1B - 02:53"]}
    audio = FakeAudio(tags)

    result = write_loudness_tags(
        Path("/library/track.flac"), measured_profile(), load_audio=lambda _: audio, save_audio=save
    )

    assert result.status is LoudnessTagWriteStatus.CHANGED
    assert tags["DESCRIPTION"] == [f"1B - 02:53 · {_LOUDNESS_COMMENT}"]


def test_flac_second_write_is_unchanged_and_does_not_duplicate_the_description() -> None:
    tags: dict[str, list[str]] = {"COMMENT": [], "DESCRIPTION": ["1B - 02:53"]}
    audio = FakeAudio(tags)

    assert (
        write_loudness_tags(
            Path("/library/track.flac"), measured_profile(), load_audio=lambda _: audio, save_audio=save
        ).status
        is LoudnessTagWriteStatus.CHANGED
    )
    expected = f"1B - 02:53 · {_LOUDNESS_COMMENT}"
    assert (
        write_loudness_tags(
            Path("/library/track.flac"), measured_profile(), load_audio=lambda _: audio, save_audio=save
        ).status
        is LoudnessTagWriteStatus.UNCHANGED
    )
    assert tags["DESCRIPTION"] == [expected]
    assert audio.save_count == 1


def test_flac_remeasurement_replaces_the_stale_loudness_suffix_and_keeps_the_prefix() -> None:
    tags: dict[str, list[str]] = {
        "COMMENT": [_LOUDNESS_COMMENT],
        "XFINAUDIO_LOUDNESS": [_PAYLOAD],
        "DESCRIPTION": [f"1B - 02:53 · {_LOUDNESS_COMMENT}"],
    }
    audio = FakeAudio(tags)

    result = write_loudness_tags(
        Path("/library/track.flac"),
        measured_profile(-7.7, 3.1, -0.2),
        load_audio=lambda _: audio,
        save_audio=save,
    )

    assert result.status is LoudnessTagWriteStatus.CHANGED
    assert tags["DESCRIPTION"] == ["1B - 02:53 · -7.7 LUFS · 3.1 LRA · -0.2 dBTP"]


def test_flac_description_that_merely_contains_a_number_is_appended_not_merged() -> None:
    tags: dict[str, list[str]] = {"COMMENT": [], "DESCRIPTION": ["recorded 02:53"]}
    audio = FakeAudio(tags)

    assert (
        write_loudness_tags(
            Path("/library/track.flac"), measured_profile(), load_audio=lambda _: audio, save_audio=save
        ).status
        is LoudnessTagWriteStatus.CHANGED
    )
    assert tags["DESCRIPTION"] == [f"recorded 02:53 · {_LOUDNESS_COMMENT}"]


def test_flac_remeasurement_of_self_produced_description_is_replaced_exactly() -> None:
    tags: dict[str, list[str]] = {"COMMENT": [], "DESCRIPTION": []}
    audio = FakeAudio(tags)

    assert (
        write_loudness_tags(
            Path("/library/track.flac"), measured_profile(), load_audio=lambda _: audio, save_audio=save
        ).status
        is LoudnessTagWriteStatus.CHANGED
    )
    assert tags["DESCRIPTION"] == [_LOUDNESS_COMMENT]

    assert (
        write_loudness_tags(
            Path("/library/track.flac"),
            measured_profile(-7.7, 3.1, -0.2),
            load_audio=lambda _: audio,
            save_audio=save,
        ).status
        is LoudnessTagWriteStatus.CHANGED
    )
    assert tags["DESCRIPTION"] == ["-7.7 LUFS · 3.1 LRA · -0.2 dBTP"]


def test_flac_multi_valued_description_keeps_foreign_values_and_replaces_only_the_loudness_value() -> None:
    tags: dict[str, list[str]] = {"COMMENT": [], "DESCRIPTION": ["my notes", _LOUDNESS_COMMENT]}
    audio = FakeAudio(tags)

    result = write_loudness_tags(
        Path("/library/track.flac"),
        measured_profile(-7.7, 3.1, -0.2),
        load_audio=lambda _: audio,
        save_audio=save,
    )

    assert result.status is LoudnessTagWriteStatus.CHANGED
    assert tags["DESCRIPTION"] == ["my notes", "-7.7 LUFS · 3.1 LRA · -0.2 dBTP"]


def test_flac_multi_valued_description_without_a_prior_loudness_value_appends_a_new_value() -> None:
    tags: dict[str, list[str]] = {"COMMENT": [], "DESCRIPTION": ["my notes", "1B - 02:53"]}
    audio = FakeAudio(tags)

    result = write_loudness_tags(
        Path("/library/track.flac"), measured_profile(), load_audio=lambda _: audio, save_audio=save
    )

    assert result.status is LoudnessTagWriteStatus.CHANGED
    assert tags["DESCRIPTION"] == ["my notes", "1B - 02:53", _LOUDNESS_COMMENT]


def test_mp4_write_never_touches_a_description_field() -> None:
    tags: dict[str, object] = {"©cmt": ["old note"], "©des": ["1B - 02:53"]}
    audio = FakeAudio(tags)

    result = write_loudness_tags(
        Path("/library/track.m4a"), measured_profile(), load_audio=lambda _: audio, save_audio=save
    )

    assert result.status is LoudnessTagWriteStatus.CHANGED
    assert tags["©des"] == ["1B - 02:53"]
    assert set(tags) == {"©cmt", "©des", _M4A_LOUDNESS_KEY}


def test_id3_write_never_touches_a_description_frame() -> None:
    tags = FakeID3Tags([TXXX(encoding=3, desc="description", text=["1B - 02:53"])])
    audio = FakeAudio(tags)

    result = write_loudness_tags(
        Path("/library/track.mp3"), measured_profile(), load_audio=lambda _: audio, save_audio=save
    )

    assert result.status is LoudnessTagWriteStatus.CHANGED
    descriptions = [frame for frame in tags.getall("TXXX") if frame.desc == "description"]
    assert len(descriptions) == 1
    assert descriptions[0].text == ["1B - 02:53"]
