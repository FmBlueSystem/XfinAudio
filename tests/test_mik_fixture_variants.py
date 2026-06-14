"""Tests for Mixed In Key metadata fixture variants.

These tests verify that `parse_mixedinkey_tags` correctly handles complete,
incomplete, conflicting, and fallback cases without requiring a real MIK
installation or private audio files.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from xfinaudio.metadata.mixedinkey_contract import parse_mixedinkey_tags

FIXTURE_PATH = Path(__file__).with_name("fixtures") / "mik_processed" / "tag_variants.json"


@pytest.fixture(scope="module")
def variants() -> dict[str, dict[str, list[str] | str]]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_complete_variant_is_complete(variants: dict[str, dict[str, list[str] | str]]) -> None:
    metadata = parse_mixedinkey_tags(variants["complete"])
    assert metadata.is_complete is True
    assert metadata.title == "Complete Track - 8A - Energy 7"
    assert metadata.artist == "Test Artist"
    assert metadata.bpm == 120.0
    assert metadata.camelot_key == "8A"
    assert metadata.energy_level == 7
    assert metadata.genre == "House"


def test_incomplete_missing_key(variants: dict[str, dict[str, list[str] | str]]) -> None:
    metadata = parse_mixedinkey_tags(variants["incomplete_missing_key"])
    assert metadata.is_complete is False
    assert metadata.camelot_key is None
    assert "camelot_key" in metadata.missing_required_fields
    assert metadata.bpm == 120.0
    assert metadata.energy_level == 7


def test_incomplete_missing_energy(variants: dict[str, dict[str, list[str] | str]]) -> None:
    metadata = parse_mixedinkey_tags(variants["incomplete_missing_energy"])
    assert metadata.is_complete is False
    assert metadata.energy_level is None
    assert "energy_level" in metadata.missing_required_fields
    assert metadata.bpm == 120.0
    assert metadata.camelot_key == "8A"


def test_incomplete_missing_bpm(variants: dict[str, dict[str, list[str] | str]]) -> None:
    metadata = parse_mixedinkey_tags(variants["incomplete_missing_bpm"])
    assert metadata.is_complete is False
    assert metadata.bpm is None
    assert "bpm" in metadata.missing_required_fields
    assert metadata.camelot_key == "8A"
    assert metadata.energy_level == 7


def test_conflicting_energy_prefers_json_energy(variants: dict[str, dict[str, list[str] | str]]) -> None:
    metadata = parse_mixedinkey_tags(variants["conflicting_energy_json_vs_text"])
    assert metadata.is_complete is True
    # JSON `energy` (level 7) takes precedence over plain `energylevel` (6).
    assert metadata.energy_level == 7


def test_bpm_fallback_to_tbpm(variants: dict[str, dict[str, list[str] | str]]) -> None:
    metadata = parse_mixedinkey_tags(variants["bpm_fallback_tbpm"])
    assert metadata.is_complete is True
    assert metadata.bpm == 125.5


def test_lowercase_variants_accepted(variants: dict[str, dict[str, list[str] | str]]) -> None:
    metadata = parse_mixedinkey_tags(variants["lowercase_variant"])
    assert metadata.is_complete is True
    assert metadata.bpm == 110.0
    assert metadata.camelot_key == "9A"
    assert metadata.energy_level == 5


def test_all_variants_have_deterministic_missing_fields(variants: dict[str, dict[str, list[str] | str]]) -> None:
    for name, raw_tags in variants.items():
        metadata = parse_mixedinkey_tags(raw_tags)
        expected_complete = name == "complete" or name in {
            "conflicting_energy_json_vs_text",
            "bpm_fallback_tbpm",
            "lowercase_variant",
        }
        assert metadata.is_complete is expected_complete, f"{name} complete mismatch"
