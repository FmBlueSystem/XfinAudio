from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest
from mutagen.id3 import COMM, TXXX

from xfinaudio.audio.loudness import LoudnessProfile, LoudnessStatus
from xfinaudio.audio.loudness_tags import LoudnessTagWriteStatus, write_loudness_tags


@dataclass
class FakeAudio:
    tags: object | None
    save_count: int = 0


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


def measured_profile() -> LoudnessProfile:
    return LoudnessProfile(
        lufs_integrated=-9.84,
        loudness_range_lra=4.23,
        true_peak_dbtp=-0.74,
        status=LoudnessStatus.MEASURED,
        engine_fingerprint="ffmpeg-test",
    )


def save(audio: FakeAudio) -> None:
    audio.save_count += 1


def test_mp3_overwrites_comment_and_writes_exact_structured_tag() -> None:
    tags = FakeID3Tags(
        [
            COMM(encoding=3, lang="eng", desc="legacy", text=["keep nothing"]),
            TXXX(encoding=3, desc="XFINAUDIO_LOUDNESS", text=["stale"]),
        ]
    )
    audio = FakeAudio(tags)

    result = write_loudness_tags(
        Path("/library/track.mp3"), measured_profile(), load_audio=lambda _: audio, save_audio=save
    )

    assert result.status is LoudnessTagWriteStatus.CHANGED
    assert audio.save_count == 1
    comments = tags.getall("COMM")
    assert len(comments) == 1
    assert comments[0].text == ["-9.8 LUFS · 4.2 LRA · -0.7 dBTP"]
    structured = [frame for frame in tags.getall("TXXX") if frame.desc == "XFINAUDIO_LOUDNESS"]
    assert len(structured) == 1
    assert structured[0].text == ["lufs=-9.8;lra=4.2;dbtp=-0.7;v=1;engine=ffmpeg-test"]


def test_id3_write_is_idempotent_and_does_not_save_again() -> None:
    audio = FakeAudio(FakeID3Tags())
    profile = measured_profile()

    assert (
        write_loudness_tags(Path("/library/track.wav"), profile, load_audio=lambda _: audio, save_audio=save).status
        is LoudnessTagWriteStatus.CHANGED
    )
    assert (
        write_loudness_tags(Path("/library/track.wav"), profile, load_audio=lambda _: audio, save_audio=save).status
        is LoudnessTagWriteStatus.UNCHANGED
    )
    assert audio.save_count == 1


def test_flac_uses_vorbis_comment_and_custom_value() -> None:
    tags: dict[str, list[str]] = {"COMMENT": ["old"], "XFINAUDIO_LOUDNESS": ["stale"]}
    audio = FakeAudio(tags)

    assert (
        write_loudness_tags(
            Path("/library/track.flac"), measured_profile(), load_audio=lambda _: audio, save_audio=save
        ).status
        is LoudnessTagWriteStatus.CHANGED
    )
    assert tags == {
        "COMMENT": ["-9.8 LUFS · 4.2 LRA · -0.7 dBTP"],
        "XFINAUDIO_LOUDNESS": ["lufs=-9.8;lra=4.2;dbtp=-0.7;v=1;engine=ffmpeg-test"],
    }
    assert (
        write_loudness_tags(
            Path("/library/track.flac"), measured_profile(), load_audio=lambda _: audio, save_audio=save
        ).status
        is LoudnessTagWriteStatus.UNCHANGED
    )
    assert audio.save_count == 1


@pytest.mark.parametrize(("suffix", "supported"), [(".aiff", True), (".m4a", False), (".ogg", False)])
def test_format_capability_map_is_explicit(suffix: str, supported: bool) -> None:
    audio = FakeAudio(FakeID3Tags())
    result = write_loudness_tags(
        Path(f"/library/track{suffix}"), measured_profile(), load_audio=lambda _: audio, save_audio=save
    )

    assert (result.status is LoudnessTagWriteStatus.CHANGED) is supported
    assert audio.save_count == int(supported)


@pytest.mark.parametrize("status", [LoudnessStatus.UNMEASURABLE, LoudnessStatus.TOO_SHORT])
def test_only_complete_measured_profiles_are_writable(status: LoudnessStatus) -> None:
    audio = FakeAudio(FakeID3Tags())
    profile = measured_profile().model_copy(update={"status": status})

    result = write_loudness_tags(Path("/library/track.mp3"), profile, load_audio=lambda _: audio, save_audio=save)

    assert result.status is LoudnessTagWriteStatus.UNSUPPORTED
    assert audio.save_count == 0


def test_measured_profile_with_missing_metric_is_not_writable() -> None:
    audio = FakeAudio(FakeID3Tags())
    profile = measured_profile().model_copy(update={"loudness_range_lra": None})

    result = write_loudness_tags(Path("/library/track.mp3"), profile, load_audio=lambda _: audio, save_audio=save)

    assert result.status is LoudnessTagWriteStatus.UNSUPPORTED
    assert audio.save_count == 0
