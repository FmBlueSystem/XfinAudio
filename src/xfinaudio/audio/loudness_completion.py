"""Headless lazy completion for disk-bound FFmpeg loudness analysis."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Protocol

from xfinaudio.audio.loudness import LoudnessProfile, LoudnessStatus
from xfinaudio.audio.loudness_tags import LoudnessTagWriteResult, LoudnessTagWriteStatus, write_loudness_tags
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.ports import TrackLoudnessProfileCachePort

_MAX_DISK_WORKERS = 2
LoudnessTagWriter = Callable[[Path, LoudnessProfile], LoudnessTagWriteResult]


class LoudnessAnalysisPort(Protocol):
    """Narrow measurement dependency required by the headless completion core."""

    def analyze(self, path: Path, *, duration_seconds: float) -> LoudnessProfile: ...


def prioritize_records(
    records: Sequence[TrackRecord],
    *,
    selected_paths: Iterable[str] = (),
    candidate_paths: Iterable[str] = (),
    visible_paths: Iterable[str] = (),
) -> list[TrackRecord]:
    """Return records once, preserving selected/candidate/visible/rest priority."""
    by_path = {record.path: record for record in records}
    ordered: list[TrackRecord] = []
    seen: set[str] = set()
    for paths in (selected_paths, candidate_paths, visible_paths, by_path):
        for path in paths:
            if path not in seen and (record := by_path.get(path)) is not None:
                ordered.append(record)
                seen.add(path)
    return ordered


class LoudnessCompletionService:
    """Replay cached results then measure at most two external-drive files at once."""

    def __init__(
        self,
        analyzer: LoudnessAnalysisPort,
        *,
        engine_fingerprint: str,
        tag_writer: LoudnessTagWriter = write_loudness_tags,
    ) -> None:
        self._analyzer = analyzer
        self._engine_fingerprint = engine_fingerprint
        self._tag_writer = tag_writer

    def cancel(self) -> None:
        """Forward lifecycle cancellation when the concrete analyzer supports it."""
        if (cancel := getattr(self._analyzer, "cancel", None)) is not None:
            cancel()

    def complete(
        self,
        records: Sequence[TrackRecord],
        repository: TrackLoudnessProfileCachePort,
        *,
        selected_paths: Iterable[str] = (),
        candidate_paths: Iterable[str] = (),
        visible_paths: Iterable[str] = (),
        force_reanalyze: bool = False,
        on_result: Callable[[str, LoudnessProfile], None] | None = None,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> dict[str, LoudnessProfile]:
        """Return cached or freshly persisted profiles, reporting every completed record."""
        ordered = prioritize_records(
            records,
            selected_paths=selected_paths,
            candidate_paths=candidate_paths,
            visible_paths=visible_paths,
        )
        cache = repository.load_loudness_profile_cache(
            [record.path for record in ordered],
            engine_fingerprint=self._engine_fingerprint,
            force_reanalyze=force_reanalyze,
        )
        results: dict[str, LoudnessProfile] = {}
        pending: list[TrackRecord] = []
        for record in ordered:
            if (profile := cache.get(record.path)) is None:
                pending.append(record)
            else:
                results[record.path] = profile
                _emit(on_result, on_progress, len(results), len(ordered), record.path, profile)

        with ThreadPoolExecutor(max_workers=_MAX_DISK_WORKERS) as pool:
            future_to_record = {
                pool.submit(self._analyzer.analyze, Path(record.path), duration_seconds=record.duration or 0.0): record
                for record in pending
            }
            for future in as_completed(future_to_record):
                record = future_to_record[future]
                try:
                    profile = future.result()
                except Exception:
                    profile = _transient_failure(self._engine_fingerprint)
                before_write = _file_identity(record.path)
                try:
                    write_result = self._tag_writer(Path(record.path), profile)
                    if write_result.status is LoudnessTagWriteStatus.CHANGED:
                        refresh_siblings = True
                    elif write_result.status in {LoudnessTagWriteStatus.UNCHANGED, LoudnessTagWriteStatus.UNSUPPORTED}:
                        refresh_siblings = False
                    else:
                        raise RuntimeError("unsafe loudness tag write result")
                except Exception:
                    profile = _transient_failure(profile.engine_fingerprint)
                    refresh_siblings = _file_identity(record.path) != before_write
                profile = _stamp_profile(profile, record)
                if refresh_siblings:
                    repository.refresh_post_metadata_identity(record.path)
                repository.update_loudness_profile(record.path, profile)
                results[record.path] = profile
                _emit(on_result, on_progress, len(results), len(ordered), record.path, profile)
        return results


def _transient_failure(engine_fingerprint: str) -> LoudnessProfile:
    return LoudnessProfile(
        lufs_integrated=None,
        loudness_range_lra=None,
        true_peak_dbtp=None,
        status=LoudnessStatus.TRANSIENT_FAILURE,
        engine_fingerprint=engine_fingerprint,
    )


def _file_identity(path: str) -> tuple[int, int] | None:
    try:
        stat = Path(path).stat()
    except OSError:
        return None
    return stat.st_mtime_ns, stat.st_size


def _stamp_profile(profile: LoudnessProfile, record: TrackRecord) -> LoudnessProfile:
    try:
        stat = Path(record.path).stat()
        mtime_ns, size_bytes = stat.st_mtime_ns, stat.st_size
    except OSError:
        mtime_ns = size_bytes = None
    return profile.model_copy(
        update={
            "source_mtime_ns": mtime_ns,
            "source_size_bytes": size_bytes,
            "source_audio_md5": record.audio_md5,
        }
    )


def _emit(
    on_result: Callable[[str, LoudnessProfile], None] | None,
    on_progress: Callable[[int, int], None] | None,
    completed: int,
    total: int,
    path: str,
    profile: LoudnessProfile,
) -> None:
    if on_result is not None:
        on_result(path, profile)
    if on_progress is not None:
        on_progress(completed, total)
