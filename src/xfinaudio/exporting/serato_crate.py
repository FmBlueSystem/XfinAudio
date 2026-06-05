"""Safe deterministic Serato crate artifact generation and fixture validation."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path, PurePosixPath

from pydantic import BaseModel, ConfigDict

SERATO_CRATE_VERSION = "1.0/Serato ScratchLive Crate"


class SeratoCrateParseError(ValueError):
    """Raised when Serato crate fixture bytes do not match the supported TLV subset."""


class ParsedSeratoCrate(BaseModel):
    """Read-only parse result for the supported Serato crate TLV subset."""

    model_config = ConfigDict(frozen=True)

    version: str | None
    paths: tuple[str, ...]
    unknown_tags: tuple[str, ...]


class SeratoCrateValidationReport(BaseModel):
    """Compatibility validation result for Serato crate fixture bytes."""

    model_config = ConfigDict(frozen=True)

    valid: bool
    version: str | None
    paths: tuple[str, ...]
    expected_paths: tuple[str, ...]
    errors: tuple[str, ...]
    unknown_tags: tuple[str, ...]


class SeratoExportPlan(BaseModel):
    """Dry-run plan for writing a caller-approved Serato crate artifact."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    crate_name: str
    relative_paths: tuple[str, ...]
    serato_root: Path
    target_path: Path
    backup_path: Path
    crate_bytes: bytes

    @property
    def track_count(self) -> int:
        """Number of tracks included in the crate artifact."""
        return len(self.relative_paths)

    def preview(self) -> dict[str, object]:
        """Return a dry-run preview without writing files."""
        return {
            "crate_name": self.crate_name,
            "target_path": str(self.target_path),
            "backup_path": str(self.backup_path),
            "track_count": self.track_count,
            "will_write": False,
        }


class SeratoWriteResult(BaseModel):
    """Result of a confirmed Serato crate artifact write."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    written_path: Path
    backup_path: Path | None
    bytes_written: int
    validated: bool
    rollback_available: bool
    rollback_action: str


def build_serato_crate_bytes(relative_paths: list[str] | tuple[str, ...]) -> bytes:
    """Build deterministic Serato crate TLV bytes for safe relative track paths."""
    validated_paths = [_validate_relative_crate_path(path) for path in relative_paths]
    records = [_tlv(b"vrsn", SERATO_CRATE_VERSION.encode("utf-16-be"))]
    for path in validated_paths:
        records.append(_tlv(b"otrk", _tlv(b"ptrk", path.encode("utf-16-be"))))
    return b"".join(records)


def parse_serato_crate_bytes(crate_bytes: bytes) -> ParsedSeratoCrate:
    """Parse supported Serato crate fixture bytes without reading or writing audio/library files."""
    version: str | None = None
    paths: list[str] = []
    unknown_tags: list[str] = []

    for tag, payload in _iter_tlv_records(crate_bytes):
        if tag == "vrsn":
            version = _decode_utf16be(payload, tag)
        elif tag == "otrk":
            paths.extend(_parse_otrk_paths(payload, unknown_tags))
        else:
            unknown_tags.append(tag)

    return ParsedSeratoCrate(version=version, paths=tuple(paths), unknown_tags=tuple(unknown_tags))


def validate_serato_crate_bytes(
    crate_bytes: bytes,
    expected_paths: list[str] | tuple[str, ...],
) -> SeratoCrateValidationReport:
    """Validate Serato crate fixture bytes against expected version and ordered paths."""
    expected_path_tuple = tuple(expected_paths)
    try:
        parsed = parse_serato_crate_bytes(crate_bytes)
    except SeratoCrateParseError as error:
        return SeratoCrateValidationReport(
            valid=False,
            version=None,
            paths=(),
            expected_paths=expected_path_tuple,
            errors=(f"malformed crate: {error}",),
            unknown_tags=(),
        )

    errors: list[str] = []
    if parsed.version != SERATO_CRATE_VERSION:
        errors.append(f"version mismatch: expected {SERATO_CRATE_VERSION}, got {parsed.version}")
    if parsed.paths != expected_path_tuple:
        errors.append("path order mismatch")

    return SeratoCrateValidationReport(
        valid=not errors,
        version=parsed.version,
        paths=parsed.paths,
        expected_paths=expected_path_tuple,
        errors=tuple(errors),
        unknown_tags=parsed.unknown_tags,
    )


def plan_serato_crate_export(
    crate_name: str, relative_paths: list[str] | tuple[str, ...], serato_root: str | Path
) -> SeratoExportPlan:
    """Create a dry-run plan for a Serato crate artifact under a caller-provided root."""
    safe_crate_name = _validate_crate_name(crate_name)
    root = Path(serato_root)
    target_path = root / "_Serato_" / "Subcrates" / f"{safe_crate_name}.crate"
    return SeratoExportPlan(
        crate_name=safe_crate_name,
        relative_paths=tuple(_validate_relative_crate_path(path) for path in relative_paths),
        serato_root=root,
        target_path=target_path,
        backup_path=target_path.with_name(f"{target_path.name}.bak"),
        crate_bytes=build_serato_crate_bytes(relative_paths),
    )


def write_serato_crate(plan: SeratoExportPlan, *, confirm: bool = False) -> SeratoWriteResult:
    """Write a planned crate only when explicitly confirmed, backing up an existing target first."""
    if not confirm:
        raise PermissionError("Serato crate export requires confirm=True")

    plan.target_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path: Path | None = None
    if plan.target_path.exists():
        backup_path = plan.backup_path
        shutil.copy2(plan.target_path, backup_path)
    plan.target_path.write_bytes(plan.crate_bytes)
    validated = validate_serato_crate_file(plan)
    return SeratoWriteResult(
        written_path=plan.target_path,
        backup_path=backup_path,
        bytes_written=len(plan.crate_bytes),
        validated=validated,
        rollback_available=True,
        rollback_action="restore_backup" if backup_path is not None else "delete_created_crate",
    )


def validate_serato_crate_file(plan: SeratoExportPlan) -> bool:
    """Validate that the written crate matches the planned deterministic artifact bytes."""
    return plan.target_path.exists() and plan.target_path.read_bytes() == plan.crate_bytes


def rollback_serato_crate_write(result: SeratoWriteResult) -> None:
    """Rollback a confirmed Serato crate write by restoring backup or deleting a new crate."""
    if result.backup_path is not None:
        shutil.copy2(result.backup_path, result.written_path)
        return
    if result.written_path.exists():
        result.written_path.unlink()


def _iter_tlv_records(data: bytes) -> Iterator[tuple[str, bytes]]:
    offset = 0
    while offset < len(data):
        if len(data) - offset < 8:
            raise SeratoCrateParseError(f"truncated TLV header at offset {offset}")

        raw_tag = data[offset : offset + 4]
        try:
            tag = raw_tag.decode("ascii")
        except UnicodeDecodeError as error:
            raise SeratoCrateParseError(f"non-ASCII TLV tag at offset {offset}") from error

        payload_length = int.from_bytes(data[offset + 4 : offset + 8], "big")
        payload_start = offset + 8
        payload_end = payload_start + payload_length
        remaining = len(data) - payload_start
        if payload_length > remaining:
            raise SeratoCrateParseError(
                f"truncated TLV payload for tag '{tag}': length {payload_length} exceeds remaining {remaining}"
            )

        yield tag, data[payload_start:payload_end]
        offset = payload_end


def _parse_otrk_paths(payload: bytes, unknown_tags: list[str]) -> tuple[str, ...]:
    paths: list[str] = []
    for tag, nested_payload in _iter_tlv_records(payload):
        if tag == "ptrk":
            paths.append(_decode_utf16be(nested_payload, "otrk.ptrk"))
        else:
            unknown_tags.append(f"otrk.{tag}")
    return tuple(paths)


def _decode_utf16be(payload: bytes, tag: str) -> str:
    try:
        return payload.decode("utf-16-be")
    except UnicodeDecodeError as error:
        raise SeratoCrateParseError(f"invalid UTF-16BE payload for tag '{tag}'") from error


def _tlv(tag: bytes, payload: bytes) -> bytes:
    if len(tag) != 4:
        raise ValueError("TLV tag must be exactly 4 bytes")
    return tag + len(payload).to_bytes(4, "big") + payload


def _validate_relative_crate_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    pure_path = PurePosixPath(normalized)
    if (
        not normalized
        or pure_path.is_absolute()
        or _looks_drive_qualified(normalized)
        or any(part in {"", ".."} for part in pure_path.parts)
    ):
        raise ValueError("Serato relative crate path must be non-empty, relative, and must not escape with '..'")
    return normalized


def _looks_drive_qualified(path: str) -> bool:
    return len(path) >= 2 and path[0].isalpha() and path[1] == ":"


def _validate_crate_name(crate_name: str) -> str:
    if not crate_name or "/" in crate_name or "\\" in crate_name or crate_name in {".", ".."}:
        raise ValueError("crate name must be non-empty and must not contain path separators")
    return crate_name


__all__ = [
    "SERATO_CRATE_VERSION",
    "ParsedSeratoCrate",
    "SeratoCrateParseError",
    "SeratoCrateValidationReport",
    "SeratoExportPlan",
    "SeratoWriteResult",
    "build_serato_crate_bytes",
    "parse_serato_crate_bytes",
    "plan_serato_crate_export",
    "rollback_serato_crate_write",
    "validate_serato_crate_bytes",
    "validate_serato_crate_file",
    "write_serato_crate",
]
