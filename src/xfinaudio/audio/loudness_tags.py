"""Format-aware, idempotent loudness tag write-back boundary."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from mutagen._file import File as MutagenFile
from mutagen.id3 import COMM, TXXX

from xfinaudio.audio.loudness import LoudnessProfile, LoudnessStatus

_LOUDNESS_TAG = "XFINAUDIO_LOUDNESS"
_ID3_SUFFIXES = frozenset({".mp3", ".wav", ".aif", ".aiff"})
_FLAC_SUFFIX = ".flac"

AudioLoader = Callable[[Path], Any | None]
AudioSaver = Callable[[Any], None]


class LoudnessTagWriteStatus(StrEnum):
    """Outcome that WU3c can use to order persistence after a tag write."""

    CHANGED = "changed"
    UNCHANGED = "unchanged"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class LoudnessTagWriteResult:
    status: LoudnessTagWriteStatus


def write_loudness_tags(
    path: Path | str,
    profile: LoudnessProfile,
    *,
    load_audio: AudioLoader | None = None,
    save_audio: AudioSaver | None = None,
) -> LoudnessTagWriteResult:
    """Overwrite v1 loudness tags only when a complete measured profile differs."""
    target = Path(path)
    if not _is_complete_measurement(profile) or _tag_family(target) is None:
        return LoudnessTagWriteResult(LoudnessTagWriteStatus.UNSUPPORTED)

    audio = (load_audio or _load_mutagen_audio)(target)
    tags = _ensure_tags(audio)
    if tags is None:
        return LoudnessTagWriteResult(LoudnessTagWriteStatus.UNSUPPORTED)

    comment, payload = _formatted_values(profile)
    changed = (
        _apply_flac_tags(tags, comment, payload)
        if target.suffix.lower() == _FLAC_SUFFIX
        else _apply_id3_tags(tags, comment, payload)
    )
    if not changed:
        return LoudnessTagWriteResult(LoudnessTagWriteStatus.UNCHANGED)
    (save_audio or _save_mutagen_audio)(audio)
    return LoudnessTagWriteResult(LoudnessTagWriteStatus.CHANGED)


def _load_mutagen_audio(path: Path) -> Any | None:
    return MutagenFile(path, easy=False)


def _save_mutagen_audio(audio: Any) -> None:
    audio.save()


def _tag_family(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix == _FLAC_SUFFIX:
        return "vorbis"
    if suffix in _ID3_SUFFIXES:
        return "id3"
    return None


def _ensure_tags(audio: Any | None) -> Any | None:
    if audio is None:
        return None
    tags = getattr(audio, "tags", None)
    if tags is None and (add_tags := getattr(audio, "add_tags", None)) is not None:
        add_tags()
        tags = getattr(audio, "tags", None)
    return tags


def _is_complete_measurement(profile: LoudnessProfile) -> bool:
    return profile.status is LoudnessStatus.MEASURED and all(
        value is not None for value in (profile.lufs_integrated, profile.loudness_range_lra, profile.true_peak_dbtp)
    )


def _formatted_values(profile: LoudnessProfile) -> tuple[str, str]:
    assert profile.lufs_integrated is not None
    assert profile.loudness_range_lra is not None
    assert profile.true_peak_dbtp is not None
    comment = (
        f"{profile.lufs_integrated:.1f} LUFS · {profile.loudness_range_lra:.1f} LRA · {profile.true_peak_dbtp:.1f} dBTP"
    )
    payload = (
        f"lufs={profile.lufs_integrated:.1f};lra={profile.loudness_range_lra:.1f};"
        f"dbtp={profile.true_peak_dbtp:.1f};v=1;engine={profile.engine_fingerprint}"
    )
    return comment, payload


def _apply_flac_tags(tags: Any, comment: str, payload: str) -> bool:
    if tags.get("COMMENT") == [comment] and tags.get(_LOUDNESS_TAG) == [payload]:
        return False
    tags["COMMENT"] = [comment]
    tags[_LOUDNESS_TAG] = [payload]
    return True


def _apply_id3_tags(tags: Any, comment: str, payload: str) -> bool:
    comments = tags.getall("COMM")
    structured = [frame for frame in tags.getall("TXXX") if frame.desc == _LOUDNESS_TAG]
    if len(comments) == len(structured) == 1 and comments[0].text == [comment] and structured[0].text == [payload]:
        return False
    tags.delall("COMM")
    tags.delall(f"TXXX:{_LOUDNESS_TAG}")
    tags.add(COMM(encoding=3, lang="eng", desc="", text=[comment]))
    tags.add(TXXX(encoding=3, desc=_LOUDNESS_TAG, text=[payload]))
    return True


__all__ = ["LoudnessTagWriteResult", "LoudnessTagWriteStatus", "write_loudness_tags"]
