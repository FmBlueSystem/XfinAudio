"""Deterministic Traktor NML playlist exporter."""

from __future__ import annotations

from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation


def build_traktor_playlist_nml(
    recommendation: PlaylistRecommendation,
    *,
    playlist_name: str = "XfinAudio Export",
) -> str:
    """Return a Traktor-compatible NML playlist string."""
    tracks = recommendation.ordered_tracks
    root = Element("NML")
    root.set("VERSION", "19")

    head = SubElement(root, "HEAD")
    head.set("COMPANY", "www.native-instruments.com")
    head.set("PROGRAM", "Traktor")

    SubElement(root, "MUSICFOLDERS")

    collection = SubElement(root, "COLLECTION")
    collection.set("ENTRIES", str(len(tracks)))

    for track in tracks:
        _append_traktor_entry(collection, track)

    if tracks:
        playlist_root = SubElement(root, "PLAYLISTS")
        node = SubElement(playlist_root, "NODE")
        node.set("TYPE", "PLAYLIST")
        node.set("NAME", playlist_name)
        for track in tracks:
            entry = SubElement(node, "ENTRY")
            entry.set("TITLE", track.title or "")
            entry.set("ARTIST", track.artist or "")
            loc = SubElement(entry, "LOCATION")
            file_name = Path(track.path).name
            parent = str(Path(track.path).parent)
            dir_path = "/" + parent.replace("/", ":") + ":"
            if not dir_path.endswith(":/:") and not dir_path.endswith("/:"):
                dir_path = dir_path.rstrip(":") + "/:"
            loc.set("FILE", file_name)
            loc.set("DIR", dir_path)
            loc.set("VOLUME", "osx")

    xml_bytes = tostring(root, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n' + xml_bytes + "\n"


def write_traktor_playlist_nml(
    recommendation: PlaylistRecommendation,
    target: str | Path,
    *,
    playlist_name: str = "XfinAudio Export",
) -> Path:
    """Write a Traktor-compatible NML playlist file."""
    target_path = Path(target)
    target_path.write_text(
        build_traktor_playlist_nml(recommendation, playlist_name=playlist_name),
        encoding="utf-8",
    )
    return target_path


def _append_traktor_entry(parent: Element, track: TrackRecord) -> None:
    entry = SubElement(parent, "ENTRY")
    entry.set("TITLE", track.title or "")
    entry.set("ARTIST", track.artist or "")

    loc = SubElement(entry, "LOCATION")
    file_name = Path(track.path).name
    parent = str(Path(track.path).parent)
    dir_path = "/" + parent.replace("/", ":") + ":"
    if not dir_path.endswith(":/:") and not dir_path.endswith("/:"):
        dir_path = dir_path.rstrip(":") + "/:"
    loc.set("FILE", file_name)
    loc.set("DIR", dir_path)
    loc.set("VOLUME", "osx")

    mod_info = SubElement(entry, "MODIFICATION_INFO")
    mod_info.set("AUTHOR_TYPE", "user")

    info = SubElement(entry, "INFO")
    if track.bpm is not None:
        info.set("PLAYTIME", "0")
        info.set("PLAYTIME_FLOAT", "0.0")
        info.set("FLAGS", "0")
        info.set("FILESIZE", "0")

    if track.bpm is not None:
        tempo = SubElement(entry, "TEMPO")
        tempo.set("BPM", f"{track.bpm:.6f}")
        tempo.set("BPM_QUALITY", "100.000000")

    if track.camelot_key:
        key_el = SubElement(entry, "MUSICAL_KEY")
        key_el.set("VALUE", track.camelot_key)


__all__ = [
    "build_traktor_playlist_nml",
    "write_traktor_playlist_nml",
]
