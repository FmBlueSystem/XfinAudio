"""Safe deterministic Serato crate artifact generation and fixture validation."""

from __future__ import annotations

import ctypes
import errno
import hashlib
import logging
import os
import secrets
import stat
import sys
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path, PurePosixPath
from typing import TypedDict

from pydantic import BaseModel, ConfigDict

LOGGER = logging.getLogger(__name__)
MAX_ANCHORED_CRATE_BYTES = 16 * 1024 * 1024
SERATO_CRATE_VERSION = "1.0/Serato ScratchLive Crate"


class SeratoCrateParseError(ValueError):
    """Raised when Serato crate fixture bytes do not match the supported TLV subset."""


class SeratoCrateWriteError(OSError):
    """A crate could not be safely published or recovered; inspect the message before retrying."""


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


FileIdentity = tuple[int, int, int, int]


class _DirectoryOptions(TypedDict, total=False):
    directory_fd: int


class _ReplacementOptions(_DirectoryOptions, total=False):
    expected_bytes: bytes
    guard: Callable[[], None]


class _UnspecifiedIdentity:
    pass


_UNSPECIFIED_IDENTITY = _UnspecifiedIdentity()


def write_serato_crate(
    plan: SeratoExportPlan,
    *,
    confirm: bool = False,
    directory_fd: int | None = None,
    expected_target_identity: FileIdentity | None | _UnspecifiedIdentity = _UNSPECIFIED_IDENTITY,
    guard: Callable[[], None] | None = None,
    expected_target_digest: str | None = None,
) -> SeratoWriteResult:
    """Write confirmed bytes with backups and readback recovery.

    With ``directory_fd``, all IO is relative to the caller's existing Subcrates
    descriptor. The caller binds that descriptor to the approved directory and
    keeps it open. Anchored writes require the exact preview target identity
    (including absence) and use the planned backup name without auto-numbering.
    ``guard`` checks caller-owned source/destination bindings before side effects,
    immediately before publication, and after readback within recovery protection.
    """
    if not confirm:
        raise PermissionError("Serato crate export requires confirm=True")

    if directory_fd is not None and len(plan.crate_bytes) > MAX_ANCHORED_CRATE_BYTES:
        raise SeratoCrateWriteError("Anchored crate exceeds the supported byte limit")
    try:
        expected = build_serato_crate_bytes(plan.relative_paths)
        if expected != plan.crate_bytes:
            raise ValueError("bytes do not match validated paths and supported TLV layout")
    except ValueError as error:
        raise SeratoCrateWriteError(f"Invalid Serato payload: {error}") from error
    if plan.backup_path.parent != plan.target_path.parent or plan.backup_path == plan.target_path:
        raise SeratoCrateWriteError("Backup must be a separate file beside the target crate")

    if directory_fd is not None and isinstance(expected_target_identity, _UnspecifiedIdentity):
        raise SeratoCrateWriteError("Anchored writes require the preview target identity (None means absent)")
    io_options: _DirectoryOptions = {} if directory_fd is None else {"directory_fd": directory_fd}
    replacement_options: _ReplacementOptions = {**io_options}
    if guard is not None:
        replacement_options["guard"] = guard
    backup_path: Path | None = None
    try:
        _run_guard(guard)
        if directory_fd is None:
            plan.target_path.parent.mkdir(parents=True, exist_ok=True)
        elif not stat.S_ISDIR(os.fstat(directory_fd).st_mode):
            raise OSError("Anchored descriptor must refer to a directory")
        previous_identity = _file_identity(plan.target_path, **io_options)
        if (
            not isinstance(expected_target_identity, _UnspecifiedIdentity)
            and previous_identity != expected_target_identity
        ):
            raise OSError("Target changed since preview; refusing replacement")
        previous = _read_regular_file(plan.target_path, **io_options) if previous_identity is not None else None
        if _file_identity(plan.target_path, **io_options) != previous_identity:
            raise OSError("Target changed concurrently; refusing backup")
        if expected_target_digest is not None and (
            previous is None or hashlib.sha256(previous).hexdigest() != expected_target_digest
        ):
            raise OSError("Target bytes changed since preview; refusing backup")
        if previous is not None:
            if directory_fd is not None:
                replacement_options["expected_bytes"] = previous
            backup_path = _create_backup(plan.backup_path, previous, **io_options)
        published_identity = _atomic_replace(
            plan.target_path, plan.crate_bytes, previous_identity, **replacement_options
        )
    except OSError as error:
        raise SeratoCrateWriteError(f"Serato write failed; inspect {plan.target_path}: {error}") from error
    try:
        if not validate_serato_crate_file(plan, **io_options):
            raise OSError("written bytes differ from the plan")
        _run_guard(guard)
        if _file_identity(plan.target_path, **io_options) != published_identity:
            raise OSError("Target changed concurrently after readback")
    except OSError as error:
        try:
            if previous is None:
                _remove_unchanged(plan.target_path, published_identity, **io_options)
            else:
                _atomic_replace(plan.target_path, previous, published_identity, **io_options)
        except OSError as recovery_error:
            raise SeratoCrateWriteError(
                f"Serato readback failed; manual recovery required for {plan.target_path}; "
                f"backup: {backup_path}. {recovery_error}"
            ) from error
        raise SeratoCrateWriteError(
            f"Serato readback failed; recovered the previous state of {plan.target_path}. Check disk access and retry."
        ) from error
    return SeratoWriteResult(
        written_path=plan.target_path,
        backup_path=backup_path,
        bytes_written=len(plan.crate_bytes),
        validated=True,
        rollback_available=True,
        rollback_action="restore_backup" if backup_path is not None else "delete_created_crate",
    )


def validate_serato_crate_file(plan: SeratoExportPlan, *, directory_fd: int | None = None) -> bool:
    """Validate that the written crate matches the planned deterministic artifact bytes."""
    io_options: _DirectoryOptions = {} if directory_fd is None else {"directory_fd": directory_fd}
    try:
        return _read_regular_file(plan.target_path, **io_options) == plan.crate_bytes
    except OSError:
        return False


def rollback_serato_crate_write(
    result: SeratoWriteResult,
    *,
    directory_fd: int | None = None,
    expected_target_identity: FileIdentity | None | _UnspecifiedIdentity = _UNSPECIFIED_IDENTITY,
    guard: Callable[[], None] | None = None,
) -> None:
    """Restore a backup atomically or remove a new crate without following symlinks."""
    io_options: _DirectoryOptions = {} if directory_fd is None else {"directory_fd": directory_fd}
    replacement_options: _ReplacementOptions = {**io_options}
    if guard is not None:
        replacement_options["guard"] = guard
    try:
        _run_guard(guard)
        identity = _file_identity(result.written_path, **io_options)
        if not isinstance(expected_target_identity, _UnspecifiedIdentity) and identity != expected_target_identity:
            raise OSError("Target changed since write; refusing rollback")
        if result.backup_path is not None:
            _atomic_replace(
                result.written_path,
                _read_regular_file(result.backup_path, **io_options),
                identity,
                **replacement_options,
            )
        elif identity is not None:
            _run_guard(guard)
            _remove_unchanged(result.written_path, identity, **io_options)
    except OSError as error:
        raise SeratoCrateWriteError(f"Rollback failed; inspect {result.written_path}: {error}") from error


def _run_guard(guard: Callable[[], None] | None) -> None:
    if guard is not None:
        try:
            guard()
        except Exception as error:
            raise OSError(f"Export guard rejected the operation: {error}") from error


def _stat_identity(info: os.stat_result) -> FileIdentity:
    return info.st_dev, info.st_ino, info.st_mtime_ns, info.st_size


def _file_identity(path: Path, *, directory_fd: int | None = None) -> FileIdentity | None:
    try:
        info = os.stat(path if directory_fd is None else path.name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(info.st_mode):
        raise OSError(f"Refusing symlink: {path}")
    if not stat.S_ISREG(info.st_mode):
        raise OSError(f"Not a regular file: {path}")
    return _stat_identity(info)


def _read_regular_file(path: Path, *, directory_fd: int | None = None) -> bytes:
    expected = _file_identity(path, directory_fd=directory_fd)
    descriptor = os.open(
        path if directory_fd is None else path.name,
        os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
        dir_fd=directory_fd,
    )
    with os.fdopen(descriptor, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise OSError(f"Not a regular file: {path}")
        if _stat_identity(info) != expected:
            raise OSError("File changed concurrently; refusing read")
        if directory_fd is not None and info.st_size > MAX_ANCHORED_CRATE_BYTES:
            raise OSError("Anchored crate exceeds the supported byte limit")
        contents = handle.read(MAX_ANCHORED_CRATE_BYTES + 1) if directory_fd is not None else handle.read()
        if directory_fd is not None and len(contents) > MAX_ANCHORED_CRATE_BYTES:
            raise OSError("Anchored crate exceeds the supported byte limit")
        if (
            _stat_identity(os.fstat(handle.fileno())) != expected
            or _file_identity(path, directory_fd=directory_fd) != expected
        ):
            raise OSError("File changed concurrently during read")
        return contents


def _unlink(path: Path, *, directory_fd: int | None = None, missing_ok: bool = False) -> None:
    try:
        os.unlink(path if directory_fd is None else path.name, dir_fd=directory_fd)
    except FileNotFoundError:
        if not missing_ok:
            raise


def _create_backup(base: Path, previous: bytes, *, directory_fd: int | None = None) -> Path:
    index = 0
    while True:
        candidate = base if index == 0 else base.with_name(f"{base.name}.{index}")
        try:
            descriptor = os.open(
                candidate if directory_fd is None else candidate.name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory_fd,
            )
            break
        except FileExistsError:
            if directory_fd is not None:
                raise
            index += 1
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(previous)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError:
        _unlink(candidate, directory_fd=directory_fd, missing_ok=True)
        raise
    return candidate


def _atomic_replace(
    target: Path,
    data: bytes,
    expected: FileIdentity | None,
    *,
    directory_fd: int | None = None,
    guard: Callable[[], None] | None = None,
    expected_bytes: bytes | None = None,
) -> FileIdentity:
    if directory_fd is None:
        descriptor, name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
        temporary = Path(name)
    else:
        temporary = target.with_name(f".xfinaudio-{secrets.token_hex(16)}.tmp")
        descriptor = os.open(
            temporary.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd
        )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
            info = os.fstat(handle.fileno())
        _run_guard(guard)
        if _file_identity(target, directory_fd=directory_fd) != expected:
            raise OSError("Target changed concurrently; refusing replacement")
        if directory_fd is None:
            os.replace(temporary, target)
        elif expected is None:
            # Atomic no-clobber publication: an arrival after the identity check
            # must fail, never turn an approved creation into an overwrite.
            _publish_exclusive(temporary.name, target.name, directory_fd)
        else:
            _replace_bound_target(temporary, target, expected, directory_fd, expected_bytes)
        return _stat_identity(info)
    finally:
        _unlink(temporary, directory_fd=directory_fd, missing_ok=True)


def _replace_bound_target(
    temporary: Path, target: Path, expected: FileIdentity, directory_fd: int, expected_bytes: bytes | None
) -> None:
    """Capture the old name, verify it, then publish without replacing any arrival.

    Unlike default atomic replacement, this anchored overwrite has a brief name
    gap. The prior backup remains throughout; an unexpected arrival is never
    overwritten. A recovery name is retained if restoring it would clobber one.
    """
    recovery = target.with_name(f".xfinaudio-recovery-{secrets.token_hex(16)}")
    if not _exclusive_rename(target.name, recovery.name, directory_fd):
        raise OSError("Filesystem lacks safe conditional overwrite; the previous crate is unchanged")
    captured = None
    discard_recovery = False
    try:
        captured = _file_identity(recovery, directory_fd=directory_fd)
        if captured != expected or (
            expected_bytes is not None and _read_regular_file(recovery, directory_fd=directory_fd) != expected_bytes
        ):
            raise OSError("Target changed at publication; refusing replacement")
        _publish_exclusive(temporary.name, target.name, directory_fd)
        discard_recovery = True
    except OSError as error:
        try:
            _publish_exclusive(recovery.name, target.name, directory_fd)
            discard_recovery = True
        except OSError as recovery_error:
            raise OSError(
                f"Concurrent target preserved; manual recovery retained at {recovery}: {recovery_error}"
            ) from error
        raise
    finally:
        if discard_recovery and captured is not None:
            try:
                if _file_identity(recovery, directory_fd=directory_fd) is not None:
                    _remove_unchanged(recovery, captured, directory_fd=directory_fd)
            except OSError:
                LOGGER.warning("Retained Serato recovery file: %s", recovery, exc_info=True)


def _exclusive_rename(source: str, target: str, directory_fd: int) -> bool:
    """Native no-replace rename; False means the platform/filesystem lacks it.

    Darwin renameatx_np uses RENAME_EXCL (0x4); Linux renameat2 uses
    RENAME_NOREPLACE (0x1). Both preserve an existing destination atomically.
    """
    name, flag = ("renameatx_np", 0x4) if sys.platform == "darwin" else ("renameat2", 0x1)
    if sys.platform not in {"darwin", "linux"}:
        return False
    try:
        function = getattr(ctypes.CDLL(None, use_errno=True), name)
    except AttributeError:
        return False
    function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    if function(directory_fd, os.fsencode(source), directory_fd, os.fsencode(target), flag) == 0:
        return True
    failure = ctypes.get_errno()
    if failure in {errno.ENOSYS, errno.EINVAL, errno.ENOTSUP, errno.EOPNOTSUPP}:
        return False
    raise OSError(failure, os.strerror(failure))


def _publish_exclusive(source: str, target: str, directory_fd: int) -> None:
    if not _exclusive_rename(source, target, directory_fd):
        # Safe fallback on platforms/filesystems without exclusive rename. If
        # hard links are unsupported too, fail closed instead of using replace.
        os.link(source, target, src_dir_fd=directory_fd, dst_dir_fd=directory_fd, follow_symlinks=False)


def _remove_unchanged(target: Path, expected: FileIdentity, *, directory_fd: int | None = None) -> None:
    if _file_identity(target, directory_fd=directory_fd) != expected:
        raise OSError("Target changed concurrently; refusing removal")
    if directory_fd is None:
        _unlink(target)
        return
    # Do not unlink the public target after a check: another writer can replace
    # that name in between. Capture it first and verify the captured inode.
    captured = target.with_name(f".xfinaudio-removal-{secrets.token_hex(16)}")
    if not _exclusive_rename(target.name, captured.name, directory_fd):
        raise OSError("Filesystem lacks safe conditional removal; target retained")
    if _file_identity(captured, directory_fd=directory_fd) != expected:
        try:
            _publish_exclusive(captured.name, target.name, directory_fd)
        except OSError as error:
            raise OSError(f"Concurrent target preserved; manual recovery retained at {captured}") from error
        raise OSError("Target changed at removal; restored the concurrent arrival")
    _unlink(captured, directory_fd=directory_fd)


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
        or "\0" in normalized
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
    "SeratoCrateWriteError",
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
