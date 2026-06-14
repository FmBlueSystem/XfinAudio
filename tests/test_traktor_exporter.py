"""Tests for Traktor NML exporter."""

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from xfinaudio.exporting.traktor_nml import build_traktor_playlist_nml, write_traktor_playlist_nml
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.strategies import default_strategy_registry


def _make_recommendation(paths: list[str]) -> PlaylistRecommendation:
    tracks = [
        TrackRecord(
            path=path,
            title=Path(path).stem,
            artist="Artist",
            bpm=128.0,
            camelot_key="11B",
            energy_level=7,
            metadata_status="complete",
        )
        for path in paths
    ]
    return PlaylistRecommendation(
        ordered_tracks=tracks,
        transition_scores=[],
        strategy=default_strategy_registry().get("build"),
        warnings=[],
        applied_controls={},
        optimizer="test",
        total_score=0.0,
    )


@pytest.fixture()
def recommendation() -> PlaylistRecommendation:
    return _make_recommendation(["/music/track1.flac"])


def test_traktor_nml_has_nml_root(recommendation: PlaylistRecommendation) -> None:
    nml = build_traktor_playlist_nml(recommendation, playlist_name="Test Set")
    root = ET.fromstring(nml)
    assert root.tag == "NML"
    assert root.attrib.get("VERSION") == "19"


def test_traktor_nml_has_collection(recommendation: PlaylistRecommendation) -> None:
    nml = build_traktor_playlist_nml(recommendation, playlist_name="Test Set")
    root = ET.fromstring(nml)
    collection = root.find("COLLECTION")
    assert collection is not None
    assert collection.attrib.get("ENTRIES") == "1"
    entries = collection.findall("ENTRY")
    assert len(entries) == 1


def test_traktor_nml_entry_has_location(recommendation: PlaylistRecommendation) -> None:
    nml = build_traktor_playlist_nml(recommendation, playlist_name="Test Set")
    root = ET.fromstring(nml)
    location = root.find(".//ENTRY/LOCATION")
    assert location is not None
    assert location.attrib.get("FILE") == "track1.flac"
    assert location.attrib.get("DIR") == "/:music/:"
    assert location.attrib.get("VOLUME") == "osx"


def test_traktor_nml_entry_has_tempo(recommendation: PlaylistRecommendation) -> None:
    nml = build_traktor_playlist_nml(recommendation, playlist_name="Test Set")
    root = ET.fromstring(nml)
    tempo = root.find(".//ENTRY/TEMPO")
    assert tempo is not None
    assert tempo.attrib.get("BPM") == "128.000000"


def test_traktor_nml_has_playlist_node(recommendation: PlaylistRecommendation) -> None:
    nml = build_traktor_playlist_nml(recommendation, playlist_name="Test Set")
    root = ET.fromstring(nml)
    playlist = root.find(".//PLAYLISTS/NODE")
    assert playlist is not None
    assert playlist.attrib.get("NAME") == "Test Set"
    assert playlist.attrib.get("TYPE") == "PLAYLIST"
    items = playlist.findall("ENTRY")
    assert len(items) == 1


def test_write_traktor_playlist_nml(tmp_path: Path, recommendation: PlaylistRecommendation) -> None:
    target = tmp_path / "test.nml"
    written = write_traktor_playlist_nml(recommendation, target, playlist_name="Test Set")
    assert written == target
    assert target.exists()
    root = ET.fromstring(target.read_text(encoding="utf-8"))
    assert root.tag == "NML"
