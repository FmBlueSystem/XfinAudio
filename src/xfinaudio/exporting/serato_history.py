"""Read-only Serato play-history and crate-membership reader (spike).

WHY copy-then-parse: XfinAudio's security invariant (SECURITY.md) forbids
mutating live Serato database files. The only live-filesystem operation in
this module is ``shutil.copyfile(source, work_dir/...)`` — a plain read of
the Serato tree plus a write into the caller-owned scratch directory. Every
parse function in this layer takes bytes only; no parse function accepts a
path, so parsing can never reach the live library.

WHY a typed-value decoder: Serato database V2 files frame records as a
4-byte ASCII tag plus a big-endian u32 payload length (same framing as the
crate parser in ``serato_crate.py``), and prefix each value with a 1-byte
type code. This spike decodes the subset it needs and records anything it
does not understand instead of failing, mirroring the crate parser's
tolerance for unknown tags.

WARNING (spike scope): the field tags decoded here (``osen``, ``pfil``,
``ttit``, ``tart``, ``ptim``) come from the synthetic test fixtures and are
NOT verified against a sanitized live Serato sample. Before production use,
confirm the real tags; the unknown-field tolerance is what makes probing
safe in the meantime.
"""

from __future__ import annotations

import shutil
import struct
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from xfinaudio.exporting.serato_crate import (
    SeratoCrateParseError,
    _iter_tlv_records,
    parse_serato_crate_bytes,
)

HISTORY_SESSIONS_SUBDIR = Path("History") / "sessions"
SUBCRATES_SUBDIR = Path("Subcrates")
HISTORY_WORK_SUBDIR = "history_sessions"
CRATE_WORK_SUBDIR = "crate_copies"

# Type codes decoded by this spike; anything else is recorded and skipped.
_FIXED_SIZE_TYPES: dict[str, int] = {"b": 1, "u": 1, "i": 4, "f": 4, "d": 8, "j": 8}

# Maximum 'o' container nesting depth. Deeper containers are recorded as
# unknown fields and skipped instead of recursing unbounded (RecursionError
# guard against adversarially nested records).
_MAX_ASSOC_DEPTH = 64

_SESSION_VERSION_TAG = "vrsn"
_SESSION_ENTRY_TAG = "osen"
_TRACK_PATH_TAG = "pfil"
_TITLE_TAG = "ttit"
_ARTIST_TAG = "tart"
_PLAYED_AT_TAG = "ptim"

# Sub-tags decoded inside each 'o' container; anything else is recorded as unknown.
_KNOWN_ASSOC_TAGS: dict[str, frozenset[str]] = {
    _SESSION_ENTRY_TAG: frozenset({_TRACK_PATH_TAG, _TITLE_TAG, _ARTIST_TAG, _PLAYED_AT_TAG}),
}


class SeratoHistoryParseError(ValueError):
    """Raised when Serato history bytes do not match the supported TLV subset."""


class ParsedSeratoHistorySession(BaseModel):
    """Read-only parse result for one Serato history session file (spike subset).

    ``track_path``/``title``/``artist``/``played_at`` are optional because the
    real session schema is not yet verified; anything unrecognized lands in
    ``unknown_fields`` instead of failing the parse.
    """

    model_config = ConfigDict(frozen=True)

    track_path: str | None
    title: str | None
    artist: str | None
    played_at: datetime | None
    unknown_fields: tuple[str, ...]


def parse_serato_history_session_bytes(session_bytes: bytes) -> ParsedSeratoHistorySession:
    """Parse one Serato history session file from bytes without touching the filesystem."""
    unknown_fields: list[str] = []
    track_path: str | None = None
    title: str | None = None
    artist: str | None = None
    played_at: datetime | None = None

    try:
        records = list(_iter_tlv_records(session_bytes))
    except SeratoCrateParseError as error:
        raise SeratoHistoryParseError(str(error)) from error

    seen_session_entries = 0
    for tag, payload in records:
        if tag == _SESSION_VERSION_TAG:
            continue  # recognized and intentionally not stored by the spike model
        if tag == _SESSION_ENTRY_TAG:
            seen_session_entries += 1
            if seen_session_entries > 1:
                # Spike limitation: only the first track entry is surfaced;
                # multi-track sessions stay recoverable via unknown_fields.
                unknown_fields.append(f"{_SESSION_ENTRY_TAG}#{seen_session_entries}")
                continue
            decoded = _decode_record(tag, payload, unknown_fields)
            if isinstance(decoded, dict):
                track_path = _as_optional_string(decoded.get(_TRACK_PATH_TAG), tag)
                title = _as_optional_string(decoded.get(_TITLE_TAG), tag)
                artist = _as_optional_string(decoded.get(_ARTIST_TAG), tag)
                played_at = _as_optional_datetime(decoded.get(_PLAYED_AT_TAG), tag)
            continue
        # Unknown root tag: record it, and surface the type code when unrecognized.
        unknown_fields.append(tag)
        _decode_record(tag, payload, unknown_fields)

    return ParsedSeratoHistorySession(
        track_path=track_path,
        title=title,
        artist=artist,
        played_at=played_at,
        unknown_fields=tuple(unknown_fields),
    )


def read_serato_history(serato_library_dir: Path, work_dir: Path) -> list[ParsedSeratoHistorySession]:
    """Enumerate, copy, and parse History/sessions/* without mutating the Serato tree."""
    _ensure_disjoint_trees(serato_library_dir, work_dir)
    sessions_dir = Path(serato_library_dir) / HISTORY_SESSIONS_SUBDIR
    if not sessions_dir.is_dir():
        return []

    (work_dir / HISTORY_WORK_SUBDIR).mkdir(parents=True, exist_ok=True)

    sessions: list[ParsedSeratoHistorySession] = []
    for source in sorted(path for path in sessions_dir.iterdir() if path.is_file()):
        copied = _copy_to_scratch(source, work_dir / HISTORY_WORK_SUBDIR)
        sessions.append(parse_serato_history_session_bytes(copied.read_bytes()))
    return sessions


def read_crate_membership(serato_library_dir: Path, work_dir: Path) -> dict[str, int]:
    """Count, per track path, how many Subcrates/*.crate contain it.

    Returns a mapping of crate-relative track path to the number of
    subcrates holding it. Copies each crate into the scratch dir before
    parsing; the live Subcrates directory is never opened for writing.
    """
    _ensure_disjoint_trees(serato_library_dir, work_dir)
    subcrates_dir = Path(serato_library_dir) / SUBCRATES_SUBDIR
    if not subcrates_dir.is_dir():
        return {}

    (work_dir / CRATE_WORK_SUBDIR).mkdir(parents=True, exist_ok=True)

    membership: dict[str, int] = {}
    for source in sorted(subcrates_dir.glob("*.crate")):
        copied = _copy_to_scratch(source, work_dir / CRATE_WORK_SUBDIR)
        for crate_path in parse_serato_crate_bytes(copied.read_bytes()).paths:
            membership[crate_path] = membership.get(crate_path, 0) + 1
    return membership


def _ensure_disjoint_trees(serato_library_dir: Path, work_dir: Path) -> None:
    """Reject overlapping serato/work trees before any mkdir or copyfile.

    Raises ValueError when ``work_dir`` is the Serato root, lives inside the
    Serato tree, or contains the Serato tree — any of which would make the
    scratch copies land inside (or around) the live library. Sibling trees
    are fine. ``Path.is_relative_to`` is available since Python 3.9 and the
    project floor is 3.11 (``datetime.UTC``), so no fallback is needed.
    """
    serato_root = Path(serato_library_dir).resolve()
    work_root = Path(work_dir).resolve()
    if work_root == serato_root or work_root.is_relative_to(serato_root) or serato_root.is_relative_to(work_root):
        raise ValueError(
            f"work_dir must not overlap the live Serato library tree: serato={serato_root} work_dir={work_root}"
        )


def _copy_to_scratch(source: Path, scratch_dir: Path) -> Path:
    """Copy one live Serato file into the caller-owned scratch dir (the only live-FS write)."""
    destination = scratch_dir / source.name
    if destination.resolve() == source.resolve():
        raise ValueError("work_dir must not overlap the live Serato library tree")
    shutil.copyfile(source, destination)
    return destination


def _decode_record(tag: str, payload: bytes, unknown_fields: list[str], depth: int = 0) -> object:
    """Decode one typed value (1-byte type code prefix); unknown types are recorded and skipped."""
    if not payload:
        unknown_fields.append(f"{tag}:empty-payload")
        return None
    type_char = chr(payload[0]) if payload[0] < 0x80 else None
    value = payload[1:]

    if type_char == "t":
        return _decode_string(tag, value)
    if type_char == "o":
        return _decode_assoc(tag, value, unknown_fields, depth)
    if type_char == "n":
        return None
    if type_char in _FIXED_SIZE_TYPES:
        return _decode_fixed(tag, type_char, value)

    if type_char is None:
        unknown_fields.append(f"{tag}:unknown-type:{payload[0]:#04x}")
    else:
        unknown_fields.append(f"{tag}:unknown-type:{type_char}")
    return None


def _decode_assoc(tag: str, value: bytes, unknown_fields: list[str], depth: int = 0) -> dict[str, object]:
    """Walk an 'o' associative-array payload: nested TLV records mapped to a dict.

    Sub-tags outside the container's known set are recorded and skipped.
    Nesting deeper than ``_MAX_ASSOC_DEPTH`` is recorded as an unknown field
    and skipped instead of recursing unbounded (RecursionError guard).
    """
    if depth >= _MAX_ASSOC_DEPTH:
        unknown_fields.append(f"{tag}:max-nesting-depth")
        return {}
    known_tags = _KNOWN_ASSOC_TAGS.get(tag, frozenset())
    decoded: dict[str, object] = {}
    try:
        for sub_tag, sub_payload in _iter_tlv_records(value):
            if known_tags and sub_tag not in known_tags:
                unknown_fields.append(f"{tag}.{sub_tag}")
                _decode_record(f"{tag}.{sub_tag}", sub_payload, unknown_fields, depth + 1)
                continue
            decoded[sub_tag] = _decode_record(f"{tag}.{sub_tag}", sub_payload, unknown_fields, depth + 1)
    except SeratoCrateParseError as error:
        raise SeratoHistoryParseError(str(error)) from error
    return decoded


def _decode_string(tag: str, value: bytes) -> str:
    """Decode a UTF-16BE string; a trailing NUL terminator is tolerated."""
    try:
        text = value.decode("utf-16-be")
    except UnicodeDecodeError as error:
        raise SeratoHistoryParseError(f"invalid UTF-16BE payload for tag '{tag}'") from error
    return text.rstrip("\x00")


def _decode_fixed(tag: str, type_char: str, value: bytes) -> object:
    """Decode a fixed-width typed value; wrong sizes are a clear error, not a crash."""
    expected = _FIXED_SIZE_TYPES[type_char]
    if len(value) != expected:
        raise SeratoHistoryParseError(
            f"tag '{tag}' expects {expected} byte(s) for type '{type_char}', got {len(value)}"
        )
    if type_char == "b":
        if value[0] not in (0, 1):
            raise SeratoHistoryParseError(f"invalid bool payload for tag '{tag}'")
        return value[0] == 1
    if type_char == "u":
        return value[0]
    if type_char == "i":
        return int.from_bytes(value, "big", signed=True)
    if type_char == "j":
        unix_ms = int.from_bytes(value, "big", signed=True)
        try:
            return datetime.fromtimestamp(unix_ms / 1000, tz=UTC)
        except (ValueError, OverflowError, OSError) as error:
            raise SeratoHistoryParseError(f"tag '{tag}' holds an out-of-range timestamp: {unix_ms} ms") from error
    if type_char == "f":
        return struct.unpack(">f", value)[0]
    return struct.unpack(">d", value)[0]  # 'd'


def _as_optional_string(value: object, tag: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise SeratoHistoryParseError(f"tag '{tag}' expected a string value")
    return value


def _as_optional_datetime(value: object, tag: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise SeratoHistoryParseError(f"tag '{tag}' expected a timestamp value")
    return value


__all__ = [
    "ParsedSeratoHistorySession",
    "SeratoHistoryParseError",
    "parse_serato_history_session_bytes",
    "read_crate_membership",
    "read_serato_history",
]
