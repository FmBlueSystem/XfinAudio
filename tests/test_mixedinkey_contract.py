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


def test_parser_converts_musical_key_notation_in_mik_json_to_camelot() -> None:
    """Mixed In Key often stores the key as a standard musical name (e.g. 'Cm') rather than
    Camelot. The parser must convert it: C minor → 5A."""
    import base64
    import json as _json

    encoded = base64.b64encode(_json.dumps({"key": "Cm", "source": "mixedinkey"}).encode()).decode()
    metadata = parse_mixedinkey_tags({"key": [encoded]})

    assert metadata.camelot_key == "5A"
    assert metadata.source_fields["camelot_key"] == "key"


def test_parser_converts_musical_key_from_initialkey_field() -> None:
    metadata = parse_mixedinkey_tags({"initialkey": ["Bbm"]})
    assert metadata.camelot_key == "3A"  # Bb minor → 3A


def test_parser_converts_major_musical_key_to_b_column() -> None:
    metadata = parse_mixedinkey_tags({"initialkey": ["G"]})
    assert metadata.camelot_key == "9B"  # G major → 9B


def test_parser_handles_enharmonic_and_unicode_sharp_flat() -> None:
    assert parse_mixedinkey_tags({"initialkey": ["G#m"]}).camelot_key == "1A"
    assert parse_mixedinkey_tags({"initialkey": ["Abm"]}).camelot_key == "1A"  # enharmonic of G#m
    assert parse_mixedinkey_tags({"initialkey": ["F#"]}).camelot_key == "2B"


def test_parser_still_accepts_native_camelot_notation() -> None:
    metadata = parse_mixedinkey_tags({"initialkey": ["8A"]})
    assert metadata.camelot_key == "8A"
