"""Tests for Rekordbox XML exporter."""

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from xfinaudio.exporting.rekordbox_xml import build_rekordbox_playlist_xml, write_rekordbox_playlist_xml
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


def test_rekordbox_xml_has_dj_playlists_root(recommendation: PlaylistRecommendation) -> None:
    xml = build_rekordbox_playlist_xml(recommendation, playlist_name="Test Set")
    root = ET.fromstring(xml)
    assert root.tag == "DJ_PLAYLISTS"
    assert root.attrib.get("Version") == "1.0.0"


def test_rekordbox_xml_has_collection(recommendation: PlaylistRecommendation) -> None:
    xml = build_rekordbox_playlist_xml(recommendation, playlist_name="Test Set")
    root = ET.fromstring(xml)
    collection = root.find("COLLECTION")
    assert collection is not None
    assert collection.attrib.get("Entries") == "2"
    tracks = collection.findall("TRACK")
    assert len(tracks) == 2


def test_rekordbox_xml_tracks_have_locations(recommendation: PlaylistRecommendation) -> None:
    xml = build_rekordbox_playlist_xml(recommendation, playlist_name="Test Set")
    root = ET.fromstring(xml)
    tracks = root.findall(".//COLLECTION/TRACK")
    assert tracks[0].attrib.get("Location") == "file://localhost/music/track1.flac"
    assert tracks[1].attrib.get("Location") == "file://localhost/music/track2.mp3"


def test_rekordbox_xml_has_playlist_node(recommendation: PlaylistRecommendation) -> None:
    xml = build_rekordbox_playlist_xml(recommendation, playlist_name="Test Set")
    root = ET.fromstring(xml)
    playlists = root.find("PLAYLISTS")
    assert playlists is not None
    node = playlists.find("NODE/NODE")
    assert node is not None
    assert node.attrib.get("Name") == "Test Set"
    assert node.attrib.get("Type") == "1"
    tracks = node.findall("TRACK")
    assert len(tracks) == 2


def test_rekordbox_xml_escapes_special_chars() -> None:
    rec = _make_recommendation(["/music/rock&roll.flac"])
    xml = build_rekordbox_playlist_xml(rec, playlist_name="Test & Demo")
    assert "&amp;" in xml
    root = ET.fromstring(xml)
    track = root.find(".//COLLECTION/TRACK")
    assert track is not None
    assert track.attrib.get("Location") == "file://localhost/music/rock&amp;roll.flac"


def test_write_rekordbox_playlist_xml(tmp_path: Path, recommendation: PlaylistRecommendation) -> None:
    target = tmp_path / "test.xml"
    written = write_rekordbox_playlist_xml(recommendation, target, playlist_name="Test Set")
    assert written == target
    assert target.exists()
    root = ET.fromstring(target.read_text(encoding="utf-8"))
    assert root.tag == "DJ_PLAYLISTS"
