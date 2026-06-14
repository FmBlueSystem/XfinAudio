"""Deterministic VirtualDJ playlist XML exporter."""

from __future__ import annotations

from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

from xfinaudio.recommendation.playlist_service import PlaylistRecommendation


def build_virtualdj_playlist_xml(
    recommendation: PlaylistRecommendation,
    *,
    playlist_name: str = "XfinAudio Export",
) -> str:
    """Return a VirtualDJ-compatible list XML string."""
    tracks = recommendation.ordered_tracks
    root = Element("VirtualFolder")
    root.set("noDuplicates", "no")
    root.set("singleDrive", "no")
    root.set("ordered", "yes")

    for index, track in enumerate(tracks):
        song = SubElement(root, "song")
        song.set("path", track.path)
        if track.title:
            song.set("title", track.title)
        if track.artist:
            song.set("artist", track.artist)
        if track.bpm is not None:
            song.set("bpm", f"{track.bpm:.1f}")
        if track.camelot_key:
            song.set("key", track.camelot_key)
        song.set("idx", str(index))

    xml_bytes = tostring(root, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes + "\n"


def write_virtualdj_playlist_xml(
    recommendation: PlaylistRecommendation,
    target: str | Path,
    *,
    playlist_name: str = "XfinAudio Export",
) -> Path:
    """Write a VirtualDJ-compatible list XML file."""
    target_path = Path(target)
    target_path.write_text(
        build_virtualdj_playlist_xml(recommendation, playlist_name=playlist_name),
        encoding="utf-8",
    )
    return target_path


__all__ = [
    "build_virtualdj_playlist_xml",
    "write_virtualdj_playlist_xml",
]
