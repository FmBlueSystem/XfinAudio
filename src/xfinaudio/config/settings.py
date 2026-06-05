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

    exact_limit: int = Field(default=20, ge=0)


class ScoringSettings(BaseModel):
    """Configuration for transition scoring policy."""

    model_config = ConfigDict(frozen=True)

    weights: ScoringWeights = DEFAULT_WEIGHTS


class ExportSettings(BaseModel):
    """Configuration for future safe export actions."""

    model_config = ConfigDict(frozen=True)

    safe_export_folder: Path | None = None


class AppSettings(BaseModel):
    """Versioned root settings model for XfinAudio."""

    model_config = ConfigDict(frozen=True)

    settings_version: int = CURRENT_SETTINGS_VERSION
    scan: ScanSettings = Field(default_factory=ScanSettings)
    optimizer: OptimizerSettings = Field(default_factory=OptimizerSettings)
    scoring: ScoringSettings = Field(default_factory=ScoringSettings)
    export: ExportSettings = Field(default_factory=ExportSettings)

    @field_validator("settings_version")
    @classmethod
    def validate_settings_version(cls, value: int) -> int:
        """Reject settings payloads from unknown future schema versions."""
        if value != CURRENT_SETTINGS_VERSION:
            raise ValueError(f"Unsupported settings version: {value}")
        return value


__all__ = [
    "AppSettings",
    "CURRENT_SETTINGS_VERSION",
    "ExportSettings",
    "OptimizerSettings",
    "ScanSettings",
    "ScoringSettings",
]
