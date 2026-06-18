"""Read-only metadata scan service for desktop library folders."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mutagen._file import File as MutagenFile

from xfinaudio.audio.batch_analyzer import analyze_paths
from xfinaudio.audio.spectral_profile import SpectralProfile, analyze_spectral_profile
from xfinaudio.genre.enrichment_service import EnrichmentService
from xfinaudio.library.models import TrackRecord
from xfinaudio.metadata.mixedinkey_contract import parse_mixedinkey_tags

LOGGER = logging.getLogger(__name__)

SUPPORTED_AUDIO_EXTENSIONS = frozenset({".aif", ".aiff", ".flac", ".m4a", ".mp3", ".wav"})

PathLister = Callable[[Path], Iterable[Path]]
TagReader = Callable[[Path], dict[str, Any] | None]
ProgressCallback = Callable[["ScanProgress"], None]
ProfileCache = dict[str, tuple[int, int, SpectralProfile]]
ProfileCacheLoader = Callable[[list[Path]], ProfileCache]


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
        parallel_spectral_analysis: bool = True,
        spectral_max_workers: int | None = None,
        previous_profile_cache: ProfileCache | None = None,
        profile_cache_loader: ProfileCacheLoader | None = None,
        resolve_spectral_profiles: bool = True,
        enrichment_service: EnrichmentService | None = None,
    ) -> list[TrackRecord]:
        """Recursively scan supported audio files under folder."""
        return scan_folder(
            folder,
            on_progress=on_progress,
            cancellation_token=cancellation_token,
            parallel_spectral_analysis=parallel_spectral_analysis,
            spectral_max_workers=spectral_max_workers,
            previous_profile_cache=previous_profile_cache,
            profile_cache_loader=profile_cache_loader,
            resolve_spectral_profiles=resolve_spectral_profiles,
            enrichment_service=enrichment_service,
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
    enrichment_service: EnrichmentService | None = None,
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
        enrichment_service: Optional genre enrichment service. When supplied and
            ``enabled``, each scanned track is enriched and a ``GenreDecision``
            is attached as ``track.genre_decision``. Provider failures are
            isolated; a track with no decision keeps ``genre_decision=None``.
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

    if previous_profile_cache is None and profile_cache_loader is not None and supported_paths:
        previous_profile_cache = profile_cache_loader(supported_paths)

    # Phase 1: read metadata for every supported file.
    metadata_by_path: dict[Path, Any] = {}
    raw_metadata_by_path: dict[Path, dict[str, Any]] = {}
    durations: dict[Path, float | None] = {}
    skipped_paths: list[Path] = []
    for path in supported_paths:
        if cancellation_token is not None and cancellation_token.is_cancelled:
            raise ScanCancelledError(
                _build_records(metadata_by_path, raw_metadata_by_path, durations, {}, skipped_paths, supported_paths)
            )
        try:
            raw_metadata = tag_reader(path)
        except Exception as exc:
            LOGGER.warning("Skipping unreadable audio file %s: %s: %s", path, exc.__class__.__name__, exc)
            skipped_paths.append(path)
            continue
        if raw_metadata is None:
            skipped_paths.append(path)
            continue
        duration = raw_metadata.pop("__duration__", None) if raw_metadata else None
        durations[path] = duration
        raw_metadata_by_path[path] = raw_metadata
        metadata_by_path[path] = parse_mixedinkey_tags(raw_metadata)

    if cancellation_token is not None and cancellation_token.is_cancelled:
        raise ScanCancelledError(
            _build_records(metadata_by_path, raw_metadata_by_path, durations, {}, skipped_paths, supported_paths)
        )

    # Phase 2: resolve spectral profiles (cache, parallel batch, sequential, or skip).
    profiles_by_path = _resolve_spectral_profiles(
        paths=list(metadata_by_path.keys()),
        parallel=parallel_spectral_analysis,
        max_workers=spectral_max_workers,
        previous_profile_cache=previous_profile_cache,
        cancellation_token=cancellation_token,
        resolve_missing=resolve_spectral_profiles,
    )

    # Phase 3: build records and emit per-file progress in deterministic order.
    records = _build_records(
        metadata_by_path,
        raw_metadata_by_path,
        durations,
        profiles_by_path,
        skipped_paths,
        supported_paths,
    )
    if enrichment_service is not None and enrichment_service.enabled:
        records = _enrich_records(records, enrichment_service)
    for processed_index, path in enumerate(supported_paths, start=1):
        if path in skipped_paths:
            _emit_progress(on_progress, processed_index, total_count, path)
            continue
        _emit_progress(on_progress, processed_index, total_count, path)
    if cancellation_token is not None and cancellation_token.is_cancelled:
        raise ScanCancelledError(records)
    return records


def _build_records(
    metadata_by_path: dict[Path, Any],
    raw_metadata_by_path: dict[Path, dict[str, Any]],
    durations: dict[Path, float | None],
    profiles_by_path: dict[Path, SpectralProfile | None],
    skipped_paths: list[Path],
    supported_paths: list[Path],
) -> list[TrackRecord]:
    """Build TrackRecord objects for every path that was not skipped."""
    records: list[TrackRecord] = []
    for path in supported_paths:
        if path in skipped_paths or path not in metadata_by_path:
            continue
        metadata = metadata_by_path[path]
        spectral_profile = profiles_by_path.get(path)
        records.append(
            TrackRecord(
                path=str(path),
                title=metadata.title,
                artist=metadata.artist,
                bpm=metadata.bpm,
                camelot_key=metadata.camelot_key,
                energy_level=metadata.energy_level,
                duration=durations[path],
                genre=metadata.genre,
                tags=metadata.tags,
                metadata_status="complete" if metadata.is_complete else "incomplete",
                missing_required_fields=metadata.missing_required_fields,
                source_fields=metadata.source_fields,
                raw_metadata=raw_metadata_by_path[path],
                spectral_profile=spectral_profile,
            )
        )
    return records


def _enrich_records(
    records: list[TrackRecord],
    enrichment_service: EnrichmentService,
) -> list[TrackRecord]:
    """Attach a ``GenreDecision`` to each track via the enrichment service.

    Only records that receive a usable decision (primary or top_n) get the
    field set. Provider failures are isolated inside the service, so this
    function itself cannot raise.
    """
    enriched: list[TrackRecord] = []
    for record in records:
        decision = enrichment_service.enrich(record)
        if decision.primary is not None or decision.top_n:
            enriched.append(record.model_copy(update={"genre_decision": decision}))
        else:
            enriched.append(record)
    return enriched


def _resolve_spectral_profiles(
    paths: list[Path],
    *,
    parallel: bool,
    max_workers: int | None,
    previous_profile_cache: ProfileCache | None,
    cancellation_token: ScanCancellationToken | None,
    resolve_missing: bool = True,
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
        )
        for path in paths_to_analyze:
            profiles[path] = results.get(str(path))
    else:
        for path in paths_to_analyze:
            if cancellation_token is not None and cancellation_token.is_cancelled:
                break
            profiles[path] = analyze_spectral_profile(path)

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
    if cached[0] == stat.st_mtime_ns and cached[1] == stat.st_size:
        return cached[2]
    return None


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
