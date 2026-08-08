"""Library metadata models for scanned audio tracks."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from xfinaudio.audio.danceability import DanceabilityProfile
from xfinaudio.audio.spectral_profile import SpectralProfile

MetadataStatus = Literal["complete", "incomplete"]


class TrackRecord(BaseModel):
    """Normalized track metadata captured by the HELP-4 scanner."""

    model_config = ConfigDict(frozen=True)

    path: str
    title: str | None = None
    artist: str | None = None
    bpm: float | None = None
    camelot_key: str | None = None
    energy_level: int | None = None
    energy_in: int | None = None
    energy_out: int | None = None
    energy_peak: int | None = None
    duration: float | None = None
    genre: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata_status: MetadataStatus = "incomplete"
    missing_required_fields: list[str] = Field(default_factory=list)
    source_fields: dict[str, str] = Field(default_factory=dict)
    raw_metadata: dict[str, Any] = Field(default_factory=dict)
    audio_md5: str | None = None
    spectral_profile: SpectralProfile | None = None
    danceability_profile: DanceabilityProfile | None = None
