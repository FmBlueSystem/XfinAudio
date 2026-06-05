from pathlib import Path

import pytest
from pydantic import ValidationError

from xfinaudio.config.settings import AppSettings, ExportSettings, ScoringSettings
from xfinaudio.library.scan_service import SUPPORTED_AUDIO_EXTENSIONS
from xfinaudio.recommendation.scoring import DEFAULT_WEIGHTS, ScoringWeights


def test_app_settings_defaults_are_versioned_and_match_current_behavior() -> None:
    settings = AppSettings()

    assert settings.settings_version == 1
    assert settings.scan.supported_extensions == SUPPORTED_AUDIO_EXTENSIONS
    assert settings.optimizer.exact_limit == 20
    assert settings.scoring.weights == DEFAULT_WEIGHTS
    assert settings.export.safe_export_folder is None


def test_app_settings_stores_safe_export_folder() -> None:
    folder = Path("/tmp/xfinaudio-safe-export")

    settings = AppSettings(export=ExportSettings(safe_export_folder=folder))

    assert settings.export.safe_export_folder == folder


def test_app_settings_does_not_infer_safe_export_folder_from_scan_folder() -> None:
    settings = AppSettings()

    assert settings.export.safe_export_folder is None


def test_app_settings_rejects_unknown_future_version() -> None:
    with pytest.raises(ValidationError, match="Unsupported settings version"):
        AppSettings(settings_version=2)


def test_app_settings_preserves_non_negative_scoring_validation() -> None:
    with pytest.raises(ValidationError, match="component weights cannot be negative"):
        AppSettings(scoring=ScoringSettings(weights=ScoringWeights(harmonic=-1.0)))
