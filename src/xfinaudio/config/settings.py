"""Versioned application settings for release-safe defaults."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from xfinaudio.library.scan_planning import SUPPORTED_AUDIO_EXTENSIONS
from xfinaudio.recommendation.loudness_policy import DEFAULT_LOUDNESS_TARGET_LUFS, DEFAULT_LOUDNESS_TOLERANCE_LU
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


class AiSettings(BaseModel):
    """Configuration for the optional AI copilot.

    Stores the PATH to the operator-owned credential env file, never the API
    key value: the key is read by the adapter at call time and must never be
    persisted in the settings file.
    """

    model_config = ConfigDict(frozen=True)

    enabled: bool = False
    env_file: Path | None = None


class LoudnessSettings(BaseModel):
    """Configuration for optional loudness-analysis scheduling."""

    model_config = ConfigDict(frozen=True)

    enabled: bool = True
    target_lufs: float = Field(default=DEFAULT_LOUDNESS_TARGET_LUFS, ge=-30.0, le=0.0)
    tolerance_lu: float = Field(default=DEFAULT_LOUDNESS_TOLERANCE_LU, ge=0.0, le=10.0)


class WindowSettings(BaseModel):
    """Persisted main-window geometry, restored on launch."""

    model_config = ConfigDict(frozen=True)

    width: int | None = None
    height: int | None = None
    x: int | None = None
    y: int | None = None


class BuildSessionSettings(BaseModel):
    """DJ build context restored across restarts for the current library.

    Deliberately not persisted: the copilot plan, the applied variant name,
    the last recommendation, derived quality/readiness reports, and
    ``playlist_removed_paths`` (rescan-reset class: a fresh scan starts a
    fresh build).
    """

    model_config = ConfigDict(frozen=True)

    excluded_paths: frozenset[str] = frozenset()
    locked_paths: frozenset[str] = frozenset()
    genre_focus: str | None = None


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
    # Additive section: an existing version-1 payload without ``ai`` stays valid
    # (the defaults hydrate), so CURRENT_SETTINGS_VERSION does not move.
    ai: AiSettings = Field(default_factory=AiSettings)
    loudness: LoudnessSettings = Field(default_factory=LoudnessSettings)
    window: WindowSettings = Field(default_factory=WindowSettings)
    build: BuildSessionSettings = Field(default_factory=BuildSessionSettings)

    @field_validator("settings_version")
    @classmethod
    def validate_settings_version(cls, value: int) -> int:
        """Reject settings payloads from unknown future schema versions."""
        if value != CURRENT_SETTINGS_VERSION:
            raise ValueError(f"Unsupported settings version: {value}")
        return value


__all__ = [
    "AiSettings",
    "AppSettings",
    "AudioSettings",
    "BuildSessionSettings",
    "CURRENT_SETTINGS_VERSION",
    "ExportSettings",
    "LibrarySettings",
    "LoudnessSettings",
    "OptimizerSettings",
    "ScanSettings",
    "ScoringSettings",
    "UiSettings",
    "WindowSettings",
]
