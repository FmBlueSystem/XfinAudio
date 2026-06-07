"""LibraryViewModel — transforms AppState into display-ready data for the library screen."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from xfinaudio.desktop.app_state import AppState
from xfinaudio.library.models import TrackRecord


@dataclass(frozen=True)
class LibraryFilters:
    search_query: str = ""
    status_filter: str | None = None  # "complete" | "incomplete" | None
    missing_field_filter: str | None = None  # "bpm" | "camelot_key" | "energy_level" | etc | None


@dataclass(frozen=True)
class TrackDisplayRow:
    path: str
    title: str
    artist: str
    bpm: str  # "128" or "—"
    musical_key: str  # "8A" or "—"
    energy: str  # "7" or "—"
    missing_fields: str  # comma-separated or "—"
    genre: str  # value or "—"
    metadata_status: str  # "complete" | "incomplete"
    display_path: str  # filename only


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

_DASH = "—"


def _fmt_bpm(bpm: float | None) -> str:
    if bpm is None or bpm == 0:
        return _DASH
    return str(int(bpm))


def _fmt_key(key: str | None) -> str:
    if not key:
        return _DASH
    return key


def _fmt_energy(energy: int | None) -> str:
    if energy is None or energy == 0:
        return _DASH
    return str(int(energy))


def _fmt_missing(fields: list[str]) -> str:
    if not fields:
        return _DASH
    return ", ".join(fields)


def _fmt_genre(genre: str | None) -> str:
    if not genre:
        return _DASH
    return genre


def _track_title_or_filename(track: TrackRecord) -> str:
    """Return title if available, otherwise the filename — used for search matching."""
    if track.title:
        return track.title
    return Path(track.path).name


def _to_display_row(track: TrackRecord) -> TrackDisplayRow:
    return TrackDisplayRow(
        path=track.path,
        title=track.title or _DASH,
        artist=track.artist or _DASH,
        bpm=_fmt_bpm(track.bpm),
        musical_key=_fmt_key(track.camelot_key),
        energy=_fmt_energy(track.energy_level),
        missing_fields=_fmt_missing(track.missing_required_fields),
        genre=_fmt_genre(track.genre),
        metadata_status=track.metadata_status,
        display_path=Path(track.path).name,
    )


# ---------------------------------------------------------------------------
# ViewModel
# ---------------------------------------------------------------------------


class LibraryViewModel:
    """Pure transformation layer — no PySide6 imports, no side effects."""

    def tracks_for_display(
        self,
        state: AppState,
        filters: LibraryFilters | None = None,
    ) -> list[TrackDisplayRow]:
        """Return formatted, filtered tracks ready for rendering."""
        if filters is None:
            filters = LibraryFilters()

        records: list[TrackRecord] = state.scanned_records

        # 1. Search query — match title (or filename if title is empty)
        # Search applies to title (falling back to filename) only, not artist.
        if filters.search_query:
            query = filters.search_query.lower()
            records = [r for r in records if query in _track_title_or_filename(r).lower()]

        # 2. Status filter
        if filters.status_filter == "complete":
            records = [r for r in records if r.metadata_status == "complete"]
        elif filters.status_filter == "incomplete":
            records = [r for r in records if r.metadata_status != "complete"]

        # 3. Missing field filter (AND with previous filters)
        if filters.missing_field_filter is not None:
            field_name = filters.missing_field_filter
            records = [r for r in records if field_name in r.missing_required_fields]

        return [_to_display_row(r) for r in records]

    def scan_button_enabled(self, state: AppState) -> bool:
        """True when a folder is selected and a scan is not already in progress."""
        return state.selected_folder is not None and not state.is_scanning

    def cancel_button_visible(self, state: AppState) -> bool:
        """True while a scan is in progress."""
        return state.is_scanning

    def status_text(self, state: AppState) -> str:
        """Human-readable library status line."""
        if state.is_scanning:
            return "Scanning…"

        tracks = state.scanned_records
        if tracks:
            total = len(tracks)
            complete = sum(1 for t in tracks if t.metadata_status == "complete")
            folder_name = state.selected_folder.name if state.selected_folder else "saved library"
            return f"{total} tracks · {complete}/{total} complete · {folder_name}"

        if state.selected_folder is None:
            return "Choose a folder to begin"

        return f"Ready to scan · {state.selected_folder.name}"

    def can_proceed(self, state: AppState) -> bool:
        """True when at least one track has been scanned."""
        return len(state.scanned_records) > 0

    def selected_count_text(self, selected_paths: list[str]) -> str:
        """Label for the current selection. Empty string when nothing is selected."""
        count = len(selected_paths)
        if count == 0:
            return ""
        return f"{count} track{'s' if count != 1 else ''} selected"
