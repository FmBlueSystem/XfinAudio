"""Format-aware, idempotent loudness tag write-back boundary."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
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


def recover_loudness_profile(
    path: Path | str, tags: Mapping[str, Any], *, audio_md5: str | None = None
) -> LoudnessProfile | None:
    """Recover only this app's v1 structured tag, stamped from current disk identity."""
    target = Path(path)
    family = _tag_family(target)
    expected_key = _LOUDNESS_TAG if family == "vorbis" else f"TXXX:{_LOUDNESS_TAG}" if family == "id3" else None
    if expected_key is None:
        return None
    payload = next(
        (_tag_text(value) for key, value in tags.items() if str(key).casefold() == expected_key.casefold()), None
    )
    if payload is None or (values := _parse_payload(payload)) is None:
        return None
    try:
        stat = target.stat()
    except OSError:
        return None
    lufs, lra, dbtp, engine = values
    return LoudnessProfile(
        lufs_integrated=lufs,
        loudness_range_lra=lra,
        true_peak_dbtp=dbtp,
        status=LoudnessStatus.MEASURED,
        engine_fingerprint=engine,
        source_mtime_ns=stat.st_mtime_ns,
        source_size_bytes=stat.st_size,
        source_audio_md5=audio_md5 if family == "vorbis" else None,
    )


def _tag_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, list | tuple) and len(value) == 1:
        return str(value[0])
    return None


def _parse_payload(payload: str) -> tuple[float, float, float, str] | None:
    fields: dict[str, str] = {}
    for part in payload.split(";"):
        key, separator, value = part.partition("=")
        key, value = key.strip(), value.strip()
        if not separator or not key or key in fields:
            return None
        fields[key] = value
    if set(fields) != {"lufs", "lra", "dbtp", "v", "engine"} or fields["v"] != "1" or not fields["engine"]:
        return None
    try:
        metrics = {key: float(fields[key]) for key in ("lufs", "lra", "dbtp")}
    except ValueError:
        return None
    if not all(math.isfinite(value) for value in metrics.values()):
        return None
    return metrics["lufs"], metrics["lra"], metrics["dbtp"], fields["engine"]


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


__all__ = ["LoudnessTagWriteResult", "LoudnessTagWriteStatus", "recover_loudness_profile", "write_loudness_tags"]
