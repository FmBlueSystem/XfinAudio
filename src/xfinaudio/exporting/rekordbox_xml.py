"""Deterministic Rekordbox XML playlist exporter."""

from __future__ import annotations

from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation


def build_rekordbox_playlist_xml(
    recommendation: PlaylistRecommendation,
    *,
    playlist_name: str = "XfinAudio Export",
) -> str:
    """Return a Rekordbox-compatible XML playlist string."""
    tracks = recommendation.ordered_tracks
    root = Element("DJ_PLAYLISTS")
    root.set("Version", "1.0.0")

    product = SubElement(root, "PRODUCT")
    product.set("Name", "rekordbox")
    product.set("Version", "6")
    product.set("Company", "Pioneer DJ")

    collection = SubElement(root, "COLLECTION")
    collection.set("Entries", str(len(tracks)))

    track_id_by_path: dict[str, int] = {}
    for index, track in enumerate(tracks, start=1):
        track_id_by_path[track.path] = index
        _append_rekordbox_track(collection, track, track_id=index)

    playlists = SubElement(root, "PLAYLISTS")
    root_node = SubElement(playlists, "NODE")
    root_node.set("Type", "0")
    root_node.set("Name", "ROOT")
    root_node.set("Count", "1")

    playlist_node = SubElement(root_node, "NODE")
    playlist_node.set("Type", "1")
    playlist_node.set("Name", playlist_name)
    playlist_node.set("Entries", str(len(tracks)))
    playlist_node.set("KeyType", "0")

    for track in tracks:
        track_el = SubElement(playlist_node, "TRACK")
        track_el.set("Key", str(track_id_by_path[track.path]))

    xml_bytes = tostring(root, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes + "\n"


def write_rekordbox_playlist_xml(
    recommendation: PlaylistRecommendation,
    target: str | Path,
    *,
    playlist_name: str = "XfinAudio Export",
) -> Path:
    """Write a Rekordbox-compatible XML playlist file."""
    target_path = Path(target)
    target_path.write_text(
        build_rekordbox_playlist_xml(recommendation, playlist_name=playlist_name),
        encoding="utf-8",
    )
    return target_path


def _append_rekordbox_track(parent: Element, track: TrackRecord, track_id: int) -> None:
    track_el = SubElement(parent, "TRACK")
    track_el.set("TrackID", str(track_id))
    track_el.set("Name", track.title or "")
    track_el.set("Artist", track.artist or "")
    track_el.set(
        "Location",
        "file://localhost" + _encode_uri_path(track.path),
    )
    if track.bpm is not None:
        track_el.set("AverageBpm", f"{track.bpm:.6f}")
    if track.camelot_key:
        track_el.set("Tonality", track.camelot_key)


def _encode_uri_path(path: str) -> str:
    """Encode a filesystem path for Rekordbox's file://localhost URI format.

    Minimal percent-encoding for characters that break XML/URI parsing.
    """
    return path.replace(" ", "%20").replace("&", "&amp;")


__all__ = [
    "build_rekordbox_playlist_xml",
    "write_rekordbox_playlist_xml",
]
