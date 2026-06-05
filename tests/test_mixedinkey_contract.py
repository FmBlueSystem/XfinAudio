import json
from pathlib import Path

from xfinaudio.metadata.mixedinkey_contract import parse_mixedinkey_tags

FIXTURES = Path(__file__).parent / "fixtures" / "mixedinkey_tag_variants.json"


def load_fixture(name: str) -> dict[str, list[str]]:
    return json.loads(FIXTURES.read_text())[name]


def test_parser_prefers_mixedinkey_json_key_and_energy_over_other_fields() -> None:
    metadata = parse_mixedinkey_tags(load_fixture("flac_mik_json_preferred"))

    assert metadata.bpm == 116.0
    assert metadata.camelot_key == "11B"
    assert metadata.energy_level == 7
    assert metadata.source_fields["camelot_key"] == "key"
    assert metadata.source_fields["energy_level"] == "energy"


def test_parser_handles_lowercase_variants_and_conflicting_energy_fallbacks() -> None:
    metadata = parse_mixedinkey_tags(load_fixture("flac_lowercase_variants_conflicting_energy"))

    assert metadata.bpm == 94.89
    assert metadata.camelot_key == "9A"
    assert metadata.energy_level == 5
    assert metadata.genre == "Hip-Hop & R&B"
    assert "Classic" in metadata.tags
    assert metadata.source_fields["energy_level"] == "energy"


def test_parser_marks_aiff_id3_tags_incomplete_when_key_and_energy_are_absent() -> None:
    metadata = parse_mixedinkey_tags(load_fixture("aiff_id3_without_mik_key_energy"))

    assert metadata.title == "Give It All You Got (Mic by Jason Willmon) - full track from MIK"
    assert metadata.bpm == 128.55
    assert metadata.camelot_key is None
    assert metadata.energy_level is None
    assert metadata.is_complete is False
    assert set(metadata.missing_required_fields) == {"camelot_key", "energy_level"}


def test_parser_uses_bpm_fallback_when_primary_candidate_is_invalid() -> None:
    metadata = parse_mixedinkey_tags(load_fixture("flac_invalid_primary_bpm_uses_fallback"))

    assert metadata.bpm == 107.67
    assert metadata.source_fields["bpm"] == "tbpm"


def test_parser_uses_energylevel_when_mixedinkey_energy_json_is_invalid() -> None:
    metadata = parse_mixedinkey_tags(load_fixture("flac_non_json_energy_uses_energylevel"))

    assert metadata.energy_level == 6
    assert metadata.source_fields["energy_level"] == "energylevel"
