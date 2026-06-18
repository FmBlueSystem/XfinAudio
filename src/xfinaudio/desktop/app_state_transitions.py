"""Pure transition helpers for desktop AppState updates."""

from __future__ import annotations

from xfinaudio.audio.spectral_profile import SpectralProfile
from xfinaudio.desktop.app_state import AppState


def apply_spectral_profile(state: AppState, *, path: str, profile: SpectralProfile) -> AppState:
    """Return a new state with a spectral profile applied to matching track records."""
    scanned_records = list(state.scanned_records)
    records_by_path = dict(state.records_by_path)

    for index, record in enumerate(scanned_records):
        if record.path == path:
            scanned_records[index] = record.model_copy(update={"spectral_profile": profile})
            break

    if path in records_by_path:
        records_by_path[path] = records_by_path[path].model_copy(update={"spectral_profile": profile})

    return state.model_copy(
        update={
            "scanned_records": scanned_records,
            "records_by_path": records_by_path,
        }
    )
