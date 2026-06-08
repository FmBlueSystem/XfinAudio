"""Read-only metadata scan service for desktop library folders."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mutagen._file import File as MutagenFile

from xfinaudio.library.models import TrackRecord
from xfinaudio.metadata.mixedinkey_contract import parse_mixedinkey_tags

LOGGER = logging.getLogger(__name__)

SUPPORTED_AUDIO_EXTENSIONS = frozenset({".aif", ".aiff", ".flac", ".m4a", ".mp3", ".wav"})

PathLister = Callable[[Path], Iterable[Path]]
TagReader = Callable[[Path], dict[str, Any] | None]
ProgressCallback = Callable[["ScanProgress"], None]


@dataclass(frozen=True)
class ScanProgress:
    """Progress update emitted after each supported audio file is processed."""

    processed_count: int
    total_count: int
    current_path: Path


class ScanCancellationToken:
    """Cooperative cancellation token for synchronous folder scans."""

    def __init__(self) -> None:
        self._is_cancelled = False

    @property
    def is_cancelled(self) -> bool:
        """Return whether cancellation has been requested."""
        return self._is_cancelled

    def cancel(self) -> None:
        """Request cooperative cancellation before the next supported file."""
        self._is_cancelled = True


class ScanCancelledError(Exception):
    """Raised when a scan is cancelled before all supported files are processed."""

    def __init__(self, records: list[TrackRecord]) -> None:
        self.records = records
        super().__init__("Scan cancelled")


class MetadataScanService:
    """Service object that scans a folder without mutating audio files."""

    def scan(
        self,
        folder: Path,
        *,
        on_progress: ProgressCallback | None = None,
        cancellation_token: ScanCancellationToken | None = None,
    ) -> list[TrackRecord]:
        """Recursively scan supported audio files under folder."""
        return scan_folder(folder, on_progress=on_progress, cancellation_token=cancellation_token)


def scan_folder(
    folder: Path,
    *,
    list_paths: PathLister | None = None,
    read_tags: TagReader | None = None,
    on_progress: ProgressCallback | None = None,
    cancellation_token: ScanCancellationToken | None = None,
) -> list[TrackRecord]:
    """Return normalized track records for supported audio files below folder.

    Args:
        folder: Root folder to scan.
        list_paths: Optional test seam for deterministic path discovery.
        read_tags: Optional test seam for deterministic metadata reads.
        on_progress: Optional callback receiving supported-file progress updates.
        cancellation_token: Optional cooperative cancellation token checked between files.
    """
    path_lister = list_paths or _recursive_paths
    tag_reader = read_tags or read_mutagen_tags
    records: list[TrackRecord] = []
    supported_paths = [
        path
        for path in sorted(path_lister(folder), key=lambda candidate: str(candidate))
        if _is_supported_audio_file(path)
    ]
    total_count = len(supported_paths)

    for processed_index, path in enumerate(supported_paths, start=1):
        if cancellation_token is not None and cancellation_token.is_cancelled:
            raise ScanCancelledError(records)
        try:
            raw_metadata = tag_reader(path)
        except Exception as exc:
            LOGGER.warning("Skipping unreadable audio file %s: %s: %s", path, exc.__class__.__name__, exc)
            _emit_progress(on_progress, processed_index, total_count, path)
            continue
        if raw_metadata is None:
            _emit_progress(on_progress, processed_index, total_count, path)
            continue
        duration = raw_metadata.pop("__duration__", None) if raw_metadata else None
        metadata = parse_mixedinkey_tags(raw_metadata)
        records.append(
            TrackRecord(
                path=str(path),
                title=metadata.title,
                artist=metadata.artist,
                bpm=metadata.bpm,
                camelot_key=metadata.camelot_key,
                energy_level=metadata.energy_level,
                duration=duration,
                genre=metadata.genre,
                tags=metadata.tags,
                metadata_status="complete" if metadata.is_complete else "incomplete",
                missing_required_fields=metadata.missing_required_fields,
                source_fields=metadata.source_fields,
                raw_metadata=raw_metadata,
            )
        )
        _emit_progress(on_progress, processed_index, total_count, path)
    if cancellation_token is not None and cancellation_token.is_cancelled:
        raise ScanCancelledError(records)
    return records


def _emit_progress(
    on_progress: ProgressCallback | None,
    processed_count: int,
    total_count: int,
    current_path: Path,
) -> None:
    if on_progress is not None:
        on_progress(
            ScanProgress(
                processed_count=processed_count,
                total_count=total_count,
                current_path=current_path,
            )
        )


def read_mutagen_tags(path: Path) -> dict[str, Any] | None:
    """Read tags and duration from an audio file with mutagen without saving or modifying it."""
    audio = MutagenFile(path, easy=False)
    if audio is None or audio.tags is None:
        return None
    tags = {str(key): _coerce_tag_value(value) for key, value in audio.tags.items()}
    if audio.info is not None and hasattr(audio.info, "length"):
        tags["__duration__"] = audio.info.length
    return tags


def _recursive_paths(folder: Path) -> Iterable[Path]:
    return folder.rglob("*")


def _is_supported_audio_file(path: Path) -> bool:
    return path.suffix.casefold() in SUPPORTED_AUDIO_EXTENSIONS


def _coerce_tag_value(value: Any) -> Any:
    text_values = getattr(value, "text", None)
    if text_values is not None:
        return [str(item) for item in text_values]
    if isinstance(value, list | tuple):
        return [str(item) for item in value]
    return str(value)
