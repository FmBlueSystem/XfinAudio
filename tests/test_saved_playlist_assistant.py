"""Saved-set responses are local, grounded and explicit about unknown metadata."""

from datetime import datetime

import pytest

from xfinaudio.application.saved_playlist_assistant import compare_saved_sets, search_saved_sets
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_models import Playlist


def sets():
    now = datetime(2026, 9, 30)
    return [Playlist(1, "Sunset", now, now, ["a", "b"]), Playlist(2, "Peak", now, now, ["b", "c"])]


def records():
    return [TrackRecord(path="a", genre="House", energy_level=3, duration=120, bpm=120)]


def test_language_search_uses_real_names_and_known_track_metadata():
    assert [p.id for p in search_saved_sets("find playlists with house", sets(), records())] == [1]
    assert [p.id for p in search_saved_sets("busca listas sunset", sets(), records())] == [1]
    assert search_saved_sets("find techno playlists", sets(), records()) == []


def test_count_filter_and_duration_require_actual_evidence():
    assert search_saved_sets("find playlists under 2 tracks", sets(), records()) == []
    assert search_saved_sets("find playlists under 5 minutes", sets(), records()) == []
    complete = [*records(), TrackRecord(path="b", duration=120)]
    assert [p.id for p in search_saved_sets("find playlists under 5 minutes", sets(), complete)] == [1]


def test_comparison_describes_coverage_and_shared_tracks_without_fabrication():
    result = compare_saved_sets(sets(), records())
    assert "Sunset" in result and "Peak" in result
    assert "3.0 (1/2 known)" in result
    assert "energy unknown (0/2 known)" in result
    assert "1 shared unique track" in result
    assert "120–120 (1/2 known)" in result
    assert "duration unknown (1/2 known)" in result


def test_comparison_requires_two_real_sets():
    with pytest.raises(ValueError, match="two"):
        compare_saved_sets(sets()[:1], records())
