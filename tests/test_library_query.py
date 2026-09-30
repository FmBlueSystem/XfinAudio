"""Offline sentence parsing uses metadata, never audio or invented facts."""

import pytest

from xfinaudio.desktop.library_query import LibraryQuery, parse_library_query
from xfinaudio.library.models import TrackRecord


def test_spanish_query_exposes_exact_constraints():
    query = parse_library_query("busca House entre 120 y 128 bpm, clave 8A, energía 4-7", ["House", "Techno"])
    assert query == LibraryQuery(genre="House", bpm_min=120, bpm_max=128, key="8A", energy_min=4, energy_max=7)
    assert query.matches(TrackRecord(path="a", genre="House", bpm=124, camelot_key="8A", energy_level=6))
    assert not query.matches(TrackRecord(path="b", genre="House"))


def test_english_query_and_local_text():
    query = parse_library_query("find deep house bpm 120-126 key 9b energy 5", ["House", "Deep House"])
    assert query.genre == "Deep House"
    assert (query.bpm_min, query.bpm_max, query.key, query.energy_min, query.energy_max) == (120, 126, "9B", 5, 5)
    assert parse_library_query('title "summer"', []).text == "summer"


@pytest.mark.parametrize(
    "text", ["bpm 140-100", "bpm 0", "energy 11", "key 13A", "play something amazing", "House Techno"]
)
def test_invalid_or_ambiguous_query_requires_edit(text):
    with pytest.raises(ValueError):
        parse_library_query(text, ["House", "Techno"])


def test_matching_filters_do_not_mutate_records_or_accept_unknown_measurements():
    track = TrackRecord(path="a", title="Summer", genre="House", bpm=124, energy_level=0)
    assert LibraryQuery(text="summer", genre="house", bpm_min=120).matches(track)
    assert not LibraryQuery(energy_min=1).matches(track)
    assert not LibraryQuery(key="8A").matches(track)
    assert track.energy_level == 0
