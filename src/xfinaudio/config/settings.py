"""Versioned application settings for release-safe defaults."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from xfinaudio.library.scan_service import SUPPORTED_AUDIO_EXTENSIONS
from xfinaudio.recommendation.scoring import DEFAULT_WEIGHTS, ScoringWeights

CURRENT_SETTINGS_VERSION = 1


class ScanSettings(BaseModel):
    """Configuration for read-only library scanning."""

    model_config = ConfigDict(frozen=True)

    supported_extensions: frozenset[str] = SUPPORTED_AUDIO_EXTENSIONS


class OptimizerSettings(BaseModel):
    """Configuration for sequence optimization limits."""

    model_config = ConfigDict(frozen=True)

    exact_limit: int = Field(default=15, ge=0)


class ScoringSettings(BaseModel):
    """Configuration for transition scoring policy."""

    model_config = ConfigDict(frozen=True)

    weights: ScoringWeights = DEFAULT_WEIGHTS
    spectral_cohesion: float = Field(default=0.5, ge=0.0, le=1.0)
    genre_cohesion: float = Field(default=0.0, ge=0.0, le=1.0)


class LibrarySettings(BaseModel):
    """Configuration for app-owned library refresh workflow."""

    model_config = ConfigDict(frozen=True)

    last_scan_folder: Path | None = None


class ExportSettings(BaseModel):
    """Configuration for future safe export actions."""

    model_config = ConfigDict(frozen=True)

    safe_export_folder: Path | None = None


class UiSettings(BaseModel):
    """Configuration for UI language and display preferences."""

    model_config = ConfigDict(frozen=True)

    language: str = ""  # Empty string = auto (system locale); "en" or "es"


class AudioSettings(BaseModel):
    """Configuration for audio preview playback."""

    model_config = ConfigDict(frozen=True)

    preview_volume: float = Field(default=0.7, ge=0.0, le=1.0)


class WindowSettings(BaseModel):
    """Persisted main-window geometry, restored on launch."""

    model_config = ConfigDict(frozen=True)

    width: int | None = None
    height: int | None = None
    x: int | None = None
    y: int | None = None


class AppSettings(BaseModel):
    """Versioned root settings model for XfinAudio."""

    model_config = ConfigDict(frozen=True)

    settings_version: int = CURRENT_SETTINGS_VERSION
    scan: ScanSettings = Field(default_factory=ScanSettings)
    optimizer: OptimizerSettings = Field(default_factory=OptimizerSettings)
    scoring: ScoringSettings = Field(default_factory=ScoringSettings)
    library: LibrarySettings = Field(default_factory=LibrarySettings)
    export: ExportSettings = Field(default_factory=ExportSettings)
    ui: UiSettings = Field(default_factory=UiSettings)
    audio: AudioSettings = Field(default_factory=AudioSettings)
    window: WindowSettings = Field(default_factory=WindowSettings)

    @field_validator("settings_version")
    @classmethod
    def validate_settings_version(cls, value: int) -> int:
        """Reject settings payloads from unknown future schema versions."""
        if value != CURRENT_SETTINGS_VERSION:
            raise ValueError(f"Unsupported settings version: {value}")
        return value


__all__ = [
    "AppSettings",
    "AudioSettings",
    "CURRENT_SETTINGS_VERSION",
    "ExportSettings",
    "LibrarySettings",
    "OptimizerSettings",
    "ScanSettings",
    "ScoringSettings",
    "UiSettings",
    "WindowSettings",
]
