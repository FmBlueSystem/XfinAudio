"""Serato library discovery and playlist-to-crate export planning."""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from xfinaudio.exporting.serato_crate import SeratoExportPlan, build_serato_crate_bytes
from xfinaudio.library.models import MetadataStatus, TrackRecord
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation

SERATO_FOLDER_NAME = "_Serato_"
SERATO_SUBCRATES_DIR = "Subcrates"
GENERATED_CRATE_ROOT = "XfinAudio"
# The short automatic name spells the month in Spanish, as the app's other dates do.
_SPANISH_MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
_UNSAFE_NAME_CHARS = re.compile(r"[/:\\]+")
_WHITESPACE = re.compile(r"\s+")


class SeratoLibrary(BaseModel):
    """Detected Serato library folder on an internal or external volume."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    serato_folder: Path
    volume_root: Path

    @property
    def subcrates_folder(self) -> Path:
        """Return the regular crate destination folder."""
        return self.serato_folder / SERATO_SUBCRATES_DIR


class SeratoLibraryNotFoundError(ValueError):
    """Raised when no usable Serato library can be selected."""


def discover_serato_libraries(
    *,
    home: Path | None = None,
    volumes_root: Path = Path("/Volumes"),
) -> list[SeratoLibrary]:
    """Find usable Serato folders in the home Music folder and mounted volumes."""
    home = home or Path.home()
    candidates: list[tuple[Path, Path]] = [
        (home / "Music" / SERATO_FOLDER_NAME, home.parent.parent if len(home.parts) >= 3 else home.parent),
        (home / SERATO_FOLDER_NAME, home.parent),
    ]

    if volumes_root.exists():
        for volume in sorted(volumes_root.iterdir(), key=lambda path: path.name.casefold()):
            if not volume.is_dir() or volume.name in {"Macintosh HD", "Recovery"}:
                continue
            candidates.append((volume / SERATO_FOLDER_NAME, volume))
            candidates.append((volume / "Music" / SERATO_FOLDER_NAME, volume))

    libraries: list[SeratoLibrary] = []
    seen: set[Path] = set()
    for serato_folder, volume_root in candidates:
        resolved_key = serato_folder.resolve() if serato_folder.exists() else serato_folder
        if resolved_key in seen:
            continue
        seen.add(resolved_key)
        if _is_usable_serato_folder(serato_folder):
            libraries.append(SeratoLibrary(serato_folder=serato_folder, volume_root=volume_root))
    return libraries


def select_serato_library_for_tracks(
    track_paths: list[str | Path] | tuple[str | Path, ...],
    libraries: list[SeratoLibrary] | tuple[SeratoLibrary, ...],
) -> SeratoLibrary:
    """Select the Serato library whose volume contains the most playlist tracks."""
    if not libraries:
        raise SeratoLibraryNotFoundError("No Serato library with a Subcrates folder was found")

    paths = [Path(path) for path in track_paths]
    scored = sorted(
        libraries,
        key=lambda library: (
            -_library_track_match_count(library, paths),
            -len(library.volume_root.parts),
            str(library.serato_folder),
        ),
    )
    return scored[0]


def plan_serato_playlist_export(
    crate_name: str,
    recommendation: PlaylistRecommendation,
    serato_folder: SeratoLibrary | str | Path,
) -> SeratoExportPlan:
    """Create a dry-run Serato crate plan for a playlist recommendation."""
    if isinstance(serato_folder, SeratoLibrary):
        library = serato_folder
        folder = library.serato_folder
    else:
        folder = Path(serato_folder)
        library = SeratoLibrary(serato_folder=folder, volume_root=folder.parent)

    if folder.name != SERATO_FOLDER_NAME:
        raise ValueError("Serato export destination must be a _Serato_ folder")
    if not (folder / SERATO_SUBCRATES_DIR).exists():
        raise ValueError("Serato export destination must contain a Subcrates folder")

    relative_paths = tuple(
        _to_serato_crate_path_for_library(Path(track.path), library) for track in recommendation.ordered_tracks
    )
    safe_crate_name = _validate_crate_name(crate_name)
    target_path = folder / SERATO_SUBCRATES_DIR / f"{safe_crate_name}.crate"
    return SeratoExportPlan(
        crate_name=safe_crate_name,
        relative_paths=relative_paths,
        serato_root=folder,
        target_path=target_path,
        backup_path=target_path.with_name(f"{target_path.name}.bak"),
        crate_bytes=build_serato_crate_bytes(relative_paths),
    )


def plan_generated_serato_playlist_export(
    recommendation: PlaylistRecommendation,
    serato_folder: SeratoLibrary | str | Path,
    *,
    generated_at: datetime | None = None,
) -> SeratoExportPlan:
    """Create a non-overwriting strategy-grouped Serato crate plan for a generated recommendation."""
    if isinstance(serato_folder, SeratoLibrary):
        library = serato_folder
        folder = library.serato_folder
    else:
        folder = Path(serato_folder)
        library = SeratoLibrary(serato_folder=folder, volume_root=folder.parent)

    if folder.name != SERATO_FOLDER_NAME:
        raise ValueError("Serato export destination must be a _Serato_ folder")
    if not (folder / SERATO_SUBCRATES_DIR).exists():
        raise ValueError("Serato export destination must contain a Subcrates folder")

    relative_paths = tuple(
        _to_serato_crate_path_for_library(Path(track.path), library) for track in recommendation.ordered_tracks
    )
    crate_name = _generated_crate_name(recommendation, generated_at=generated_at)
    target_folder = folder / SERATO_SUBCRATES_DIR
    target_path = _unique_generated_crate_path(target_folder, crate_name)
    return SeratoExportPlan(
        crate_name=target_path.stem,
        relative_paths=relative_paths,
        serato_root=folder,
        target_path=target_path,
        backup_path=target_path.with_name(f"{target_path.name}.bak"),
        crate_bytes=build_serato_crate_bytes(relative_paths),
    )


def plan_copilot_variant_serato_playlist_export(
    variant_name: str,
    recommendation: PlaylistRecommendation,
    serato_folder: SeratoLibrary | str | Path,
    *,
    generated_at: datetime | None = None,
) -> SeratoExportPlan:
    """Create a non-overwriting Serato crate plan for a selected Prep Copilot variant."""
    if isinstance(serato_folder, SeratoLibrary):
        library = serato_folder
        folder = library.serato_folder
    else:
        folder = Path(serato_folder)
        library = SeratoLibrary(serato_folder=folder, volume_root=folder.parent)

    if folder.name != SERATO_FOLDER_NAME:
        raise ValueError("Serato export destination must be a _Serato_ folder")
    if not (folder / SERATO_SUBCRATES_DIR).exists():
        raise ValueError("Serato export destination must contain a Subcrates folder")

    relative_paths = tuple(
        _to_serato_crate_path_for_library(Path(track.path), library) for track in recommendation.ordered_tracks
    )
    # The chosen format is style plus date. A variant is one more set of the same
    # style exported today, so it takes the same short name and the numbered suffix
    # keeps it apart; `variant_name` stays in the signature for its existing callers.
    crate_name = _generated_crate_name(recommendation, generated_at=generated_at)
    target_folder = folder / SERATO_SUBCRATES_DIR
    target_path = _unique_generated_crate_path(target_folder, crate_name)
    return SeratoExportPlan(
        crate_name=target_path.stem,
        relative_paths=relative_paths,
        serato_root=folder,
        target_path=target_path,
        backup_path=target_path.with_name(f"{target_path.name}.bak"),
        crate_bytes=build_serato_crate_bytes(relative_paths),
    )


def plan_metadata_status_serato_export(
    records: list[TrackRecord] | tuple[TrackRecord, ...],
    status: MetadataStatus,
    serato_folder: SeratoLibrary | str | Path,
    *,
    generated_at: datetime | None = None,
) -> SeratoExportPlan:
    """Create a non-overwriting Serato worklist crate for complete or incomplete metadata status."""
    if isinstance(serato_folder, SeratoLibrary):
        library = serato_folder
        folder = library.serato_folder
    else:
        folder = Path(serato_folder)
        library = SeratoLibrary(serato_folder=folder, volume_root=folder.parent)

    if folder.name != SERATO_FOLDER_NAME:
        raise ValueError("Serato export destination must be a _Serato_ folder")
    if not (folder / SERATO_SUBCRATES_DIR).exists():
        raise ValueError("Serato export destination must contain a Subcrates folder")

    matching_records = [record for record in records if record.metadata_status == status]
    if not matching_records:
        raise ValueError(f"No {status} tracks are available for Serato metadata export")

    relative_paths = tuple(_to_serato_crate_path_for_library(Path(record.path), library) for record in matching_records)
    crate_name = _metadata_status_crate_name(status, len(matching_records), generated_at=generated_at)
    target_folder = folder / SERATO_SUBCRATES_DIR
    target_path = _unique_crate_path(target_folder, crate_name)
    return SeratoExportPlan(
        crate_name=target_path.stem,
        relative_paths=relative_paths,
        serato_root=folder,
        target_path=target_path,
        backup_path=target_path.with_name(f"{target_path.name}.bak"),
        crate_bytes=build_serato_crate_bytes(relative_paths),
    )


def plan_metadata_missing_field_serato_export(
    records: list[TrackRecord] | tuple[TrackRecord, ...],
    missing_field: str,
    serato_folder: SeratoLibrary | str | Path,
    *,
    generated_at: datetime | None = None,
) -> SeratoExportPlan:
    """Create a non-overwriting Serato worklist crate for one missing metadata field."""
    if isinstance(serato_folder, SeratoLibrary):
        library = serato_folder
        folder = library.serato_folder
    else:
        folder = Path(serato_folder)
        library = SeratoLibrary(serato_folder=folder, volume_root=folder.parent)

    if folder.name != SERATO_FOLDER_NAME:
        raise ValueError("Serato export destination must be a _Serato_ folder")
    if not (folder / SERATO_SUBCRATES_DIR).exists():
        raise ValueError("Serato export destination must contain a Subcrates folder")

    matching_records = [
        record
        for record in records
        if record.metadata_status == "incomplete" and missing_field in record.missing_required_fields
    ]
    if not matching_records:
        raise ValueError(f"No tracks are missing {missing_field} for Serato metadata export")

    relative_paths = tuple(_to_serato_crate_path_for_library(Path(record.path), library) for record in matching_records)
    crate_name = _metadata_missing_field_crate_name(missing_field, len(matching_records), generated_at=generated_at)
    target_folder = folder / SERATO_SUBCRATES_DIR
    target_path = _unique_crate_path(target_folder, crate_name)
    return SeratoExportPlan(
        crate_name=target_path.stem,
        relative_paths=relative_paths,
        serato_root=folder,
        target_path=target_path,
        backup_path=target_path.with_name(f"{target_path.name}.bak"),
        crate_bytes=build_serato_crate_bytes(relative_paths),
    )


def to_serato_crate_path(file_path: str | Path) -> str:
    """Convert an absolute macOS file path into Serato's drive-relative crate path."""
    path = Path(file_path)
    parts = path.parts
    if len(parts) >= 4 and parts[0] == "/" and parts[1] == "Volumes":
        return "/".join(parts[3:])
    if path.is_absolute():
        return str(path).lstrip("/").replace("\\", "/")
    return str(path).replace("\\", "/")


def _to_serato_crate_path_for_library(file_path: Path, library: SeratoLibrary) -> str:
    try:
        return file_path.relative_to(library.volume_root).as_posix()
    except ValueError:
        return to_serato_crate_path(file_path)


def _is_usable_serato_folder(path: Path) -> bool:
    return path.name == SERATO_FOLDER_NAME and (path / SERATO_SUBCRATES_DIR).is_dir()


def _library_track_match_count(library: SeratoLibrary, track_paths: list[Path]) -> int:
    count = 0
    for path in track_paths:
        try:
            path.relative_to(library.volume_root)
        except ValueError:
            continue
        count += 1
    return count


def _validate_crate_name(crate_name: str) -> str:
    if not crate_name or "/" in crate_name or "\\" in crate_name or crate_name in {".", ".."}:
        raise ValueError("crate name must be non-empty and must not contain path separators")
    return crate_name


def _generated_crate_name(
    recommendation: PlaylistRecommendation,
    *,
    generated_at: datetime | None = None,
) -> str:
    """Return «XfinAudio%%<strategy> <day>-<month>»: style plus a short local date."""
    generated_at = generated_at or datetime.now()
    strategy = _sanitize_name(recommendation.strategy.display_name)
    short_date = f"{generated_at.day}-{_SPANISH_MONTHS[generated_at.month - 1]}"
    return _sanitize_name(f"{GENERATED_CRATE_ROOT}%%{strategy} {short_date}")


def _metadata_status_crate_name(
    status: MetadataStatus,
    count: int,
    *,
    generated_at: datetime | None = None,
) -> str:
    display_status = status.capitalize()
    group = _sanitize_name(f"{GENERATED_CRATE_ROOT}%%Metadata%%{display_status}")
    leaf_name = _crate_leaf_name(count=count, generated_at=generated_at)
    return f"{group}%%{leaf_name}"


def _metadata_missing_field_crate_name(
    missing_field: str,
    count: int,
    *,
    generated_at: datetime | None = None,
) -> str:
    display_field = _metadata_field_display_name(missing_field)
    group = _sanitize_name(f"{GENERATED_CRATE_ROOT}%%Metadata%%Missing {display_field}")
    leaf_name = _crate_leaf_name(count=count, generated_at=generated_at)
    return f"{group}%%{leaf_name}"


def _crate_leaf_name(
    *,
    count: int,
    generated_at: datetime | None,
) -> str:
    """Worklist leaf: the count and a compact stamp under the status or field folder."""
    generated_at = generated_at or datetime.now()
    stamp = generated_at.strftime("%m%d-%H%M")
    track_word = "track" if count == 1 else "tracks"
    return _sanitize_name(f"{count} {track_word} · {stamp}")


def _metadata_field_display_name(field_name: str) -> str:
    labels = {
        "bpm": "BPM",
        "camelot_key": "Key",
        "energy_level": "Energy",
    }
    return labels.get(field_name, field_name.replace("_", " ").title())


def _unique_crate_path(target_folder: Path, crate_name: str) -> Path:
    """Worklist crates keep their `-2` suffix so existing worklist names do not change."""
    return _first_free_crate_path(target_folder, crate_name, numbered=lambda attempt: f"{crate_name}-{attempt}")


def _unique_generated_crate_path(target_folder: Path, crate_name: str) -> Path:
    """An automatic name never replaces an earlier export: it takes " (2)", " (3)"..."""
    return _first_free_crate_path(target_folder, crate_name, numbered=lambda attempt: f"{crate_name} ({attempt})")


def _first_free_crate_path(target_folder: Path, crate_name: str, *, numbered: Callable[[int], str]) -> Path:
    target_path = target_folder / f"{crate_name}.crate"
    if not target_path.exists():
        return target_path

    attempt = 2
    while True:
        candidate = target_folder / f"{numbered(attempt)}.crate"
        if not candidate.exists():
            return candidate
        attempt += 1


def _sanitize_name(value: str) -> str:
    sanitized = _UNSAFE_NAME_CHARS.sub("-", value).strip()
    sanitized = _WHITESPACE.sub(" ", sanitized)
    sanitized = sanitized.strip(" .")
    if not sanitized or sanitized in {".", ".."}:
        raise ValueError("generated crate name must contain at least one safe character")
    return sanitized


__all__ = [
    "SERATO_FOLDER_NAME",
    "SERATO_SUBCRATES_DIR",
    "SeratoLibrary",
    "SeratoLibraryNotFoundError",
    "discover_serato_libraries",
    "plan_copilot_variant_serato_playlist_export",
    "plan_generated_serato_playlist_export",
    "plan_metadata_missing_field_serato_export",
    "plan_metadata_status_serato_export",
    "plan_serato_playlist_export",
    "select_serato_library_for_tracks",
    "to_serato_crate_path",
]
