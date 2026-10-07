"""Malformed tempo metadata must never imply a safe, perfect transition."""

import base64
import json
import math

import pytest

from xfinaudio.library.models import TrackRecord
from xfinaudio.metadata.mixedinkey_contract import parse_mixedinkey_tags
from xfinaudio.quality.dj_readiness import build_dj_readiness_report
from xfinaudio.quality.recommendation_quality import build_quality_report
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.scoring import bpm_difference_percent, score_transition
from xfinaudio.recommendation.strategies import default_strategy_registry

INVALID = [None, float("nan"), float("inf"), -float("inf"), 0.0, -10.0]


@pytest.mark.parametrize("value", [*INVALID, "", "garbage", "120,5", 0.001])
def test_parser_rejects_unusable_tempo(value: object) -> None:
    metadata = parse_mixedinkey_tags({"bpm": value, "initialkey": "8A", "energylevel": "5"})
    assert metadata.bpm is None
    assert not metadata.is_complete
    assert metadata.missing_required_fields == ["bpm"]
    assert "bpm" not in metadata.source_fields


@pytest.mark.parametrize("value", INVALID)
def test_invalid_flat_and_beatgrid_tempos_allow_fallback(value: float | None) -> None:
    blob = base64.b64encode(json.dumps({"source": "mixedinkey", "tempo": value}).encode()).decode()
    assert parse_mixedinkey_tags({"beatgrid": blob}).bpm is None
    metadata = parse_mixedinkey_tags({"beatgrid": blob, "bpm": value, "tbpm": "128.55"})
    assert metadata.bpm == 128.55
    assert metadata.source_fields["bpm"] == "tbpm"


@pytest.mark.parametrize("value,expected", [(" 128.555 ", 128.56), ("1.2e2", 120), (["94.89"], 94.89), (350, 350)])
def test_valid_tempo_formats_keep_precision(value: object, expected: float) -> None:
    assert parse_mixedinkey_tags({"bpm": value}).bpm == expected


def track(path: str, bpm: float | None) -> TrackRecord:
    return TrackRecord(path=path, bpm=bpm, camelot_key="8A", energy_level=5, metadata_status="complete")


@pytest.mark.parametrize("value", INVALID)
@pytest.mark.parametrize("reverse", [False, True])
def test_malformed_persisted_tempo_fails_closed(value: float | None, reverse: bool) -> None:
    tracks = [track("invalid", value), track("valid", 120)]
    if reverse:
        tracks.reverse()
    score = score_transition(tracks[0], tracks[1])
    assert score.total_score == 0
    assert score.warnings
    assert all(math.isfinite(v) for v in score.component_scores.values())
    assert score.mixability_score is None or math.isfinite(score.mixability_score)
    recommendation = PlaylistRecommendation(
        ordered_tracks=tracks,
        transition_scores=[score],
        strategy=default_strategy_registry().get("build"),
        warnings=[],
        applied_controls={},
        optimizer="manual-test",
        total_score=score.total_score,
    )
    report = build_dj_readiness_report(recommendation, build_quality_report(recommendation))
    assert report.status == "blocked"
    for label in ("Metadatos requeridos", "Continuidad de BPM"):
        assert next(check.status for check in report.checks if check.label == label) == "blocked"


@pytest.mark.parametrize("value", INVALID[1:])
def test_public_bpm_difference_is_conservative_and_finite(value: float) -> None:
    assert bpm_difference_percent(value, 120) == 100
    assert bpm_difference_percent(120, value) == 100
