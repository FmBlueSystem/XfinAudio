import base64
import json
from pathlib import Path

import pytest

from xfinaudio.metadata.mixedinkey_contract import PARSED_TAG_KEYS, parse_mixedinkey_tags

FIXTURES = Path(__file__).parent / "fixtures" / "mixedinkey_tag_variants.json"


def load_fixture(name: str) -> dict[str, list[str]]:
    return json.loads(FIXTURES.read_text())[name]


def encode_tag_json(payload: dict[str, object]) -> str:
    return base64.b64encode(json.dumps(payload).encode()).decode()


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


@pytest.mark.parametrize(
    ("raw_tags", "field_name"),
    [
        ({"grouping": ["2"]}, "grouping"),
        ({"comment": ["5A - [⚡️7 | 💃0.75]"]}, "comment"),
        ({"publisher": ["Energy 7"]}, "publisher"),
    ],
)
def test_parser_does_not_fabricate_energy_from_unreliable_fields(
    raw_tags: dict[str, list[str]], field_name: str
) -> None:
    metadata = parse_mixedinkey_tags(raw_tags)

    assert metadata.energy_level is None, field_name


def test_parser_energylevel_outranks_unreliable_energy_fields() -> None:
    metadata = parse_mixedinkey_tags(
        {
            "energylevel": ["6"],
            "grouping": ["2"],
            "comment": ["5A - [⚡️7 | 💃0.75]"],
            "publisher": ["Energy 8"],
        }
    )

    assert metadata.energy_level == 6
    assert metadata.source_fields["energy_level"] == "energylevel"


def test_parser_uses_mixedinkey_energy_blob_as_primary_energy_source() -> None:
    energy = encode_tag_json({"source": "mixedinkey", "energyLevel": 9})

    metadata = parse_mixedinkey_tags({"energy": [energy]})

    assert metadata.energy_level == 9
    assert metadata.source_fields["energy_level"] == "energy"


def test_parser_uses_plain_energylevel_when_energy_blob_is_absent() -> None:
    metadata = parse_mixedinkey_tags({"energylevel": ["4"]})

    assert metadata.energy_level == 4
    assert metadata.source_fields["energy_level"] == "energylevel"


def test_parser_uses_title_as_final_energy_fallback() -> None:
    metadata = parse_mixedinkey_tags({"title": ["Track - Energy 8"]})

    assert metadata.energy_level == 8
    assert metadata.source_fields["energy_level"] == "title"


def test_parsed_tag_keys_exclude_unreliable_energy_fields() -> None:
    assert {
        "title",
        "tit2",
        "artist",
        "tpe1",
        "tcon",
        "bpm",
        "tbpm",
        "ibpm",
        "key",
        "initialkey",
        "tkey",
        "energy",
        "energylevel",
        "genre",
        "mood",
        "subgenre",
        "dj_zone",
        "genre_category",
    } == PARSED_TAG_KEYS


def test_parser_prefers_mixedinkey_beatgrid_tempo_over_a_third_party_bpm_tag() -> None:
    """`beatgrid` carries Mixed In Key's own tempo; plain `bpm` may be another tool's.

    Measured on the real library: a third-party organizer overwrote the flat tag
    fields on 9,826 of 10,392 files. Roughly 4% of them disagree with the
    beatgrid, several by a 4/3 triplet-feel ratio. Verified blind on the file
    below by re-running Mixed In Key against a tag-stripped copy: it returned
    151.05, matching the beatgrid, not the 80.28 in the `bpm` tag.
    """
    import base64
    import json as _json

    encoded = base64.b64encode(
        _json.dumps({"source": "mixedinkey", "tempo": 151.0471801757812, "algorithm": 12}).encode()
    ).decode()

    metadata = parse_mixedinkey_tags({"beatgrid": [encoded], "bpm": ["80.280000"]})

    assert metadata.bpm == 151.05
    assert metadata.source_fields["bpm"] == "beatgrid"


def test_parser_falls_back_to_the_bpm_tag_when_the_beatgrid_is_not_mixedinkey() -> None:
    """Only Mixed In Key's own beatgrid outranks the flat tag."""
    import base64
    import json as _json

    foreign = base64.b64encode(_json.dumps({"source": "othertool", "tempo": 99.0}).encode()).decode()

    metadata = parse_mixedinkey_tags({"beatgrid": [foreign], "bpm": ["128.00"]})

    assert metadata.bpm == 128.0
    assert metadata.source_fields["bpm"] == "bpm"


def test_parser_ignores_a_malformed_beatgrid_tempo() -> None:
    import base64
    import json as _json

    broken = base64.b64encode(_json.dumps({"source": "mixedinkey", "tempo": "n/a"}).encode()).decode()

    metadata = parse_mixedinkey_tags({"beatgrid": [broken], "bpm": ["128.00"]})

    assert metadata.bpm == 128.0


def test_parser_corrects_half_time_mixedinkey_tempo_from_beat_onsets() -> None:
    spacing = 0.35475
    beatgrid = encode_tag_json(
        {
            "source": "mixedinkey",
            "tempo": 84.59,
            "algorithm": 12,
            "beats": [index * spacing for index in range(32)],
        }
    )

    metadata = parse_mixedinkey_tags({"beatgrid": [beatgrid]})

    assert metadata.bpm == round(60 / spacing, 2)
    assert metadata.source_fields["bpm"] == "beatgrid"


def test_parser_keeps_normal_mixedinkey_tempo_with_matching_beat_onsets() -> None:
    spacing = 0.46875
    beatgrid = encode_tag_json(
        {
            "source": "mixedinkey",
            "tempo": 128.0,
            "beats": [index * spacing for index in range(32)],
        }
    )

    metadata = parse_mixedinkey_tags({"beatgrid": [beatgrid]})

    assert metadata.bpm == 128.0


def test_parser_keeps_mixedinkey_tempo_when_onset_ratio_is_out_of_band() -> None:
    spacing = 0.4
    beatgrid = encode_tag_json(
        {
            "source": "mixedinkey",
            "tempo": 100.0,
            "beats": [index * spacing for index in range(32)],
        }
    )

    metadata = parse_mixedinkey_tags({"beatgrid": [beatgrid]})

    assert metadata.bpm == 100.0


@pytest.mark.parametrize(
    "beats",
    [
        None,
        [index * 0.35475 for index in range(15)],
        [0.0, *[index * 0.35475 for index in range(1, 15)], 14 * 0.35475],
        [*range(15), "invalid"],
    ],
    ids=["missing", "too-few", "not-increasing", "non-numeric"],
)
def test_parser_keeps_declared_tempo_for_malformed_beat_onsets(beats: object) -> None:
    payload: dict[str, object] = {"source": "mixedinkey", "tempo": 84.59}
    if beats is not None:
        payload["beats"] = beats

    metadata = parse_mixedinkey_tags({"beatgrid": [encode_tag_json(payload)]})

    assert metadata.bpm == 84.59


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


@pytest.mark.parametrize(
    "cues",
    [
        [
            {"name": "Energy 5", "time": 15000},
            {"name": "Energy 8", "time": 120000},
            {"name": "Energy 6", "time": 210000},
        ],
        [
            {"name": "Energy 6", "time": 210000},
            {"name": "Energy 5", "time": 15000},
            {"name": "Energy 8", "time": 120000},
        ],
    ],
    ids=["chronological", "out-of-order"],
)
def test_parser_derives_energy_curve_from_chronologically_ordered_cues(cues: list[dict[str, object]]) -> None:
    metadata = parse_mixedinkey_tags({"cuepoints": [encode_tag_json({"cues": cues})]})

    assert (metadata.energy_in, metadata.energy_out, metadata.energy_peak) == (5, 6, 8)


def test_parser_uses_single_energy_cue_for_the_entire_curve() -> None:
    cuepoints = encode_tag_json({"cues": [{"name": "Energy 7", "time": 234844.11}]})

    metadata = parse_mixedinkey_tags({"cuepoints": [cuepoints]})

    assert (metadata.energy_in, metadata.energy_out, metadata.energy_peak) == (7, 7, 7)


def test_parser_ignores_non_energy_and_out_of_range_cues() -> None:
    cuepoints = encode_tag_json(
        {
            "cues": [
                {"name": "Drop", "time": 1000},
                {"name": "Energy 0", "time": 2000},
                {"name": "Energy 11", "time": 3000},
                {"name": "Intro", "time": 4000},
            ]
        }
    )

    metadata = parse_mixedinkey_tags({"cuepoints": [cuepoints]})

    assert (metadata.energy_in, metadata.energy_out, metadata.energy_peak) == (None, None, None)


@pytest.mark.parametrize(
    "cuepoints",
    [
        "not-base64",
        base64.b64encode(b"not-json").decode(),
        encode_tag_json({}),
        encode_tag_json({"cues": "not-a-list"}),
        encode_tag_json({"cues": [{"name": "Energy 5", "time": "soon"}]}),
        encode_tag_json({"cues": ["not-a-dict"]}),
    ],
    ids=["corrupt-base64", "not-json", "missing-cues", "cues-not-list", "non-numeric-time", "cue-not-dict"],
)
def test_parser_returns_empty_energy_curve_for_malformed_cuepoints(cuepoints: str) -> None:
    metadata = parse_mixedinkey_tags({"cuepoints": [cuepoints]})

    assert (metadata.energy_in, metadata.energy_out, metadata.energy_peak) == (None, None, None)


def test_parser_energy_curve_is_optional_and_cuepoint_blob_is_not_persisted() -> None:
    metadata = parse_mixedinkey_tags(
        {
            "bpm": ["128"],
            "initialkey": ["8A"],
            "energylevel": ["7"],
        }
    )

    assert (metadata.energy_in, metadata.energy_out, metadata.energy_peak) == (None, None, None)
    assert metadata.missing_required_fields == []
    assert metadata.is_complete is True
    assert "cuepoints" not in PARSED_TAG_KEYS
