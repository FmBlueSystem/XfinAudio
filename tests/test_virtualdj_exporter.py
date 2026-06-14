"""Tests for VirtualDJ XML exporter."""

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from xfinaudio.exporting.virtualdj_xml import build_virtualdj_playlist_xml, write_virtualdj_playlist_xml
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.strategies import default_strategy_registry


def _make_recommendation(paths: list[str]) -> PlaylistRecommendation:
    tracks = [
        TrackRecord(
            path=path,
            title=Path(path).stem.replace("track", "Track ").replace("_", " ").strip(),
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
    return _make_recommendation(["/music/track1.flac", "/music/track2.mp3"])


def test_virtualdj_xml_has_virtual_folder_root(recommendation: PlaylistRecommendation) -> None:
    xml = build_virtualdj_playlist_xml(recommendation, playlist_name="Test Set")
    root = ET.fromstring(xml)
    assert root.tag == "VirtualFolder"
    assert root.attrib.get("ordered") == "yes"


def test_virtualdj_xml_has_song_entries(recommendation: PlaylistRecommendation) -> None:
    xml = build_virtualdj_playlist_xml(recommendation, playlist_name="Test Set")
    root = ET.fromstring(xml)
    songs = root.findall("song")
    assert len(songs) == 2
    assert songs[0].attrib.get("path") == "/music/track1.flac"
    assert songs[0].attrib.get("title") == "Track 1"
    assert songs[0].attrib.get("artist") == "Artist"
    assert songs[0].attrib.get("bpm") == "128.0"
    assert songs[0].attrib.get("key") == "11B"
    assert songs[0].attrib.get("idx") == "0"


def test_virtualdj_xml_uses_absolute_paths(recommendation: PlaylistRecommendation) -> None:
    xml = build_virtualdj_playlist_xml(recommendation, playlist_name="Test Set")
    root = ET.fromstring(xml)
    songs = root.findall("song")
    assert songs[0].attrib.get("path").startswith("/")


def test_write_virtualdj_playlist_xml(tmp_path: Path, recommendation: PlaylistRecommendation) -> None:
    target = tmp_path / "Test Set.xml"
    written = write_virtualdj_playlist_xml(recommendation, target, playlist_name="Test Set")
    assert written == target
    assert target.exists()
    root = ET.fromstring(target.read_text(encoding="utf-8"))
    assert root.tag == "VirtualFolder"
