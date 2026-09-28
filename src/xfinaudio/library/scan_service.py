"""Read-only metadata scan service for desktop library folders."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mutagen._file import File as MutagenFile

from xfinaudio.audio.analyzer import LibrosaSpectralAnalyzer, SpectralAnalyzer
from xfinaudio.audio.batch_analyzer import analyze_paths
from xfinaudio.audio.loudness_tags import MP4_LOUDNESS_TAG, recover_loudness_profile
from xfinaudio.audio.spectral_profile import CURRENT_ANALYSIS_VERSION, SpectralProfile
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_planning import (
    SUPPORTED_AUDIO_EXTENSIONS as SUPPORTED_AUDIO_EXTENSIONS,
)
from xfinaudio.library.scan_planning import (
    plan_supported_audio_paths,
)
from xfinaudio.metadata.mixedinkey_contract import PARSED_TAG_KEYS, parse_mixedinkey_tags

LOGGER = logging.getLogger(__name__)

PathLister = Callable[[Path], Iterable[Path]]
TagReader = Callable[[Path], dict[str, Any] | None]
ProgressCallback = Callable[["ScanProgress"], None]
ProfileCache = dict[str, tuple[int, int, SpectralProfile]]

ProfileCacheLoader = Callable[[list[Path]], ProfileCache]


@dataclass(frozen=True)
class ScanProgress:
    """Progress update emitted as each supported audio file is processed.

    ``record`` carries the just-built track so application services can persist
    incrementally without the scan service knowing about repositories. It is
    ``None`` for files that were skipped, and its spectral profile is not
    resolved yet: the completion save owns the profile-complete records.
    """

    processed_count: int
    total_count: int
    current_path: Path
    record: TrackRecord | None = None


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
        list_paths: PathLister | None = None,
        read_tags: TagReader | None = None,
        on_progress: ProgressCallback | None = None,
        cancellation_token: ScanCancellationToken | None = None,
        parallel_spectral_analysis: bool = True,
        spectral_max_workers: int | None = None,
        previous_profile_cache: ProfileCache | None = None,
        profile_cache_loader: ProfileCacheLoader | None = None,
        resolve_spectral_profiles: bool = True,
        spectral_analyzer: SpectralAnalyzer | None = None,
    ) -> list[TrackRecord]:
        """Recursively scan supported audio files under folder."""
        return scan_folder(
            folder,
            list_paths=list_paths,
            read_tags=read_tags,
            on_progress=on_progress,
            cancellation_token=cancellation_token,
            parallel_spectral_analysis=parallel_spectral_analysis,
            spectral_max_workers=spectral_max_workers,
            previous_profile_cache=previous_profile_cache,
            profile_cache_loader=profile_cache_loader,
            resolve_spectral_profiles=resolve_spectral_profiles,
            spectral_analyzer=spectral_analyzer,
        )


def scan_folder(
    folder: Path,
    *,
    list_paths: PathLister | None = None,
    read_tags: TagReader | None = None,
    on_progress: ProgressCallback | None = None,
    cancellation_token: ScanCancellationToken | None = None,
    parallel_spectral_analysis: bool = False,
    spectral_max_workers: int | None = None,
    previous_profile_cache: ProfileCache | None = None,
    profile_cache_loader: ProfileCacheLoader | None = None,
    resolve_spectral_profiles: bool = True,
    spectral_analyzer: SpectralAnalyzer | None = None,
) -> list[TrackRecord]:
    """Return normalized track records for supported audio files below folder.

    Args:
        folder: Root folder to scan.
        list_paths: Optional test seam for deterministic path discovery.
        read_tags: Optional test seam for deterministic metadata reads.
        on_progress: Optional callback receiving supported-file progress updates.
        cancellation_token: Optional cooperative cancellation token checked between files.
        parallel_spectral_analysis: When True, analyze spectral profiles in batch
            after metadata is read. Default False preserves the original per-file
            behavior for callers that rely on it.
        spectral_max_workers: Upper bound for the parallel batch analyzer.
        previous_profile_cache: Optional ``path -> (mtime_ns, size_bytes, profile)``
            cache populated from a previous scan. Hits skip analysis entirely.
        profile_cache_loader: Optional callable that receives the list of paths
            about to be analyzed and returns a profile cache. Used by workflow
            services to populate the cache from persistent storage lazily.
        resolve_spectral_profiles: When False, only profiles available in
            ``previous_profile_cache`` are attached; missing profiles are left
            as ``None`` so a background worker can compute them later. Default
            True preserves the original synchronous behavior.
        spectral_analyzer: Optional analyzer boundary used for both sequential
            and batch spectral analysis.
    """
    path_lister = list_paths or _recursive_paths
    tag_reader = read_tags or read_mutagen_tags
    records: list[TrackRecord] = []
    supported_paths = plan_supported_audio_paths(folder, list_paths=path_lister)
    total_count = len(supported_paths)

    if previous_profile_cache is None and profile_cache_loader is not None and supported_paths:
        previous_profile_cache = profile_cache_loader(supported_paths)

    # Phase 1: read metadata for every supported file, reporting progress per
    # file as it is read. This loop is where a real multi-hour library scan
    # spends its time, so a progress signal emitted only after the last file
    # would drive neither a live ETA nor an incremental save.
    metadata_by_path: dict[Path, Any] = {}
    raw_metadata_by_path: dict[Path, dict[str, Any]] = {}
    durations: dict[Path, float | None] = {}
    audio_md5s: dict[Path, str | None] = {}
    skipped_paths: list[Path] = []
    for processed_index, path in enumerate(supported_paths, start=1):
        if cancellation_token is not None and cancellation_token.is_cancelled:
            raise ScanCancelledError(
                _build_records(
                    metadata_by_path,
                    raw_metadata_by_path,
                    durations,
                    audio_md5s,
                    {},
                    skipped_paths,
                    supported_paths,
                )
            )
        try:
            raw_metadata = tag_reader(path)
        except Exception as exc:
            LOGGER.warning("Skipping unreadable audio file %s: %s: %s", path, exc.__class__.__name__, exc)
            skipped_paths.append(path)
            _emit_progress(on_progress, processed_index, total_count, path, None)
            continue
        if raw_metadata is None:
            skipped_paths.append(path)
            _emit_progress(on_progress, processed_index, total_count, path, None)
            continue
        duration = raw_metadata.pop("__duration__", None) if raw_metadata else None
        audio_md5 = raw_metadata.pop("__audio_md5__", None) if raw_metadata else None
        durations[path] = duration
        audio_md5s[path] = audio_md5
        raw_metadata_by_path[path] = raw_metadata
        metadata = parse_mixedinkey_tags(raw_metadata)
        metadata_by_path[path] = metadata
        if on_progress is not None:
            _emit_progress(
                on_progress,
                processed_index,
                total_count,
                path,
                _build_record(path, metadata, raw_metadata, duration, audio_md5, None),
            )

    if cancellation_token is not None and cancellation_token.is_cancelled:
        raise ScanCancelledError(
            _build_records(
                metadata_by_path,
                raw_metadata_by_path,
                durations,
                audio_md5s,
                {},
                skipped_paths,
                supported_paths,
            )
        )

    # Phase 2: resolve spectral profiles (cache, parallel batch, sequential, or skip).
    profiles_by_path = _resolve_spectral_profiles(
        paths=list(metadata_by_path.keys()),
        parallel=parallel_spectral_analysis,
        max_workers=spectral_max_workers,
        previous_profile_cache=previous_profile_cache,
        cancellation_token=cancellation_token,
        resolve_missing=resolve_spectral_profiles,
        spectral_analyzer=spectral_analyzer,
    )

    # Phase 3: build the final records in deterministic order. Progress was
    # already reported file by file during phase 1.
    records = _build_records(
        metadata_by_path,
        raw_metadata_by_path,
        durations,
        audio_md5s,
        profiles_by_path,
        skipped_paths,
        supported_paths,
    )
    if cancellation_token is not None and cancellation_token.is_cancelled:
        raise ScanCancelledError(records)
    return records


def _build_records(
    metadata_by_path: dict[Path, Any],
    raw_metadata_by_path: dict[Path, dict[str, Any]],
    durations: dict[Path, float | None],
    audio_md5s: dict[Path, str | None],
    profiles_by_path: dict[Path, SpectralProfile | None],
    skipped_paths: list[Path],
    supported_paths: list[Path],
) -> list[TrackRecord]:
    """Build TrackRecord objects for every path that was not skipped."""
    records: list[TrackRecord] = []
    for path in supported_paths:
        if path in skipped_paths or path not in metadata_by_path:
            continue
        records.append(
            _build_record(
                path,
                metadata_by_path[path],
                raw_metadata_by_path[path],
                durations[path],
                audio_md5s[path],
                profiles_by_path.get(path),
            )
        )
    return records


def _build_record(
    path: Path,
    metadata: Any,
    raw_metadata: dict[str, Any],
    duration: float | None,
    audio_md5: str | None,
    spectral_profile: SpectralProfile | None,
) -> TrackRecord:
    """Build one track record from already-read metadata."""
    return TrackRecord(
        path=str(path),
        title=metadata.title,
        artist=metadata.artist,
        bpm=metadata.bpm,
        camelot_key=metadata.camelot_key,
        energy_level=metadata.energy_level,
        energy_in=metadata.energy_in,
        energy_out=metadata.energy_out,
        energy_peak=metadata.energy_peak,
        duration=duration,
        genre=metadata.genre,
        release_year=metadata.release_year,
        tags=metadata.tags,
        metadata_status="complete" if metadata.is_complete else "incomplete",
        missing_required_fields=metadata.missing_required_fields,
        source_fields=metadata.source_fields,
        raw_metadata=_retained_raw_metadata(raw_metadata),
        audio_md5=audio_md5,
        spectral_profile=spectral_profile,
        loudness_profile=recover_loudness_profile(path, raw_metadata, audio_md5=audio_md5),
    )


def _retained_raw_metadata(raw_metadata: dict[str, Any]) -> dict[str, Any]:
    """Keep only the tags the parser reads.

    parse_mixedinkey_tags() has already run by this point, so dropping the rest
    costs nothing. On a real 10,392-track library this is the difference between
    261 MB and ~2 MB of retained and persisted tag payload.
    """
    return {key: value for key, value in raw_metadata.items() if key.casefold() in PARSED_TAG_KEYS}


def _resolve_spectral_profiles(
    paths: list[Path],
    *,
    parallel: bool,
    max_workers: int | None,
    previous_profile_cache: ProfileCache | None,
    cancellation_token: ScanCancellationToken | None,
    resolve_missing: bool = True,
    spectral_analyzer: SpectralAnalyzer | None = None,
) -> dict[Path, SpectralProfile | None]:
    """Return a spectral profile for each path, using cache or analysis."""
    profiles: dict[Path, SpectralProfile | None] = {}
    paths_to_analyze: list[Path] = []

    for path in paths:
        cached_profile = _lookup_previous_profile(path, previous_profile_cache)
        if cached_profile is not None:
            profiles[path] = cached_profile
            continue
        if resolve_missing:
            paths_to_analyze.append(path)

    if not paths_to_analyze:
        return profiles

    if parallel and len(paths_to_analyze) > 1:
        results = analyze_paths(
            paths_to_analyze,
            max_workers=max_workers,
            executor="thread",
            cancellation_token=cancellation_token,
            spectral_analyzer=spectral_analyzer,
        )
        for path in paths_to_analyze:
            profiles[path] = results.get(str(path))
    else:
        analyzer = spectral_analyzer or LibrosaSpectralAnalyzer()
        for path in paths_to_analyze:
            if cancellation_token is not None and cancellation_token.is_cancelled:
                break
            profiles[path] = analyzer.analyze(path)

    return profiles


def _lookup_previous_profile(
    path: Path,
    previous_profile_cache: ProfileCache | None,
) -> SpectralProfile | None:
    """Return a cached profile if the file identity still matches."""
    if previous_profile_cache is None:
        return None
    try:
        stat = path.stat()
    except OSError:
        return None
    cached = previous_profile_cache.get(str(path))
    if cached is None:
        return None
    if (
        cached[0] == stat.st_mtime_ns
        and cached[1] == stat.st_size
        and cached[2].analysis_version == CURRENT_ANALYSIS_VERSION
    ):
        return cached[2]
    return None


def _emit_progress(
    on_progress: ProgressCallback | None,
    processed_count: int,
    total_count: int,
    current_path: Path,
    record: TrackRecord | None,
) -> None:
    if on_progress is not None:
        on_progress(
            ScanProgress(
                processed_count=processed_count,
                total_count=total_count,
                current_path=current_path,
                record=record,
            )
        )


def read_mutagen_tags(path: Path) -> dict[str, Any] | None:
    """Read tags and duration from an audio file with mutagen without saving or modifying it."""
    audio = MutagenFile(path, easy=False)
    if audio is None or audio.tags is None:
        return None
    tags = {str(key): _coerce_tag_value(value, key=str(key)) for key, value in audio.tags.items()}
    if audio.info is not None and hasattr(audio.info, "length"):
        tags["__duration__"] = audio.info.length
    try:
        signature = getattr(audio.info, "md5_signature", 0)
        if signature:
            tags["__audio_md5__"] = format(signature, "032x")
    except Exception:
        pass
    return tags


def _recursive_paths(folder: Path) -> Iterable[Path]:
    return folder.rglob("*")


def _coerce_tag_value(value: Any, *, key: str = "") -> Any:
    if key == MP4_LOUDNESS_TAG and isinstance(value, list | tuple):
        return list(value)
    text_values = getattr(value, "text", None)
    if text_values is not None:
        return [str(item) for item in text_values]
    if isinstance(value, list | tuple):
        return [str(item) for item in value]
    # Binary frames (APIC artwork, GEOB Serato blobs) have no .text, and their
    # repr() escapes every byte to \xNN — 4x the payload. Summarize instead.
    payload = getattr(value, "data", None)
    if isinstance(payload, bytes | bytearray):
        return f"<binary:{type(value).__name__}:{len(payload)} bytes>"
    if isinstance(value, bytes | bytearray):
        return f"<binary:{len(value)} bytes>"
    return str(value)
