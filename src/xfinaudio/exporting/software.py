"""Pure export software catalog."""

from __future__ import annotations

PLAYLIST_FILE_EXTENSIONS = {
    "Rekordbox": ".xml",
    "Traktor": ".nml",
    "VirtualDJ": ".xml",
}


def playlist_file_extension(software: str) -> str:
    """Return the playlist file extension for supported non-Serato software."""
    extension = PLAYLIST_FILE_EXTENSIONS.get(software)
    if extension is None:
        raise ValueError(f"Unknown export software: {software}")
    return extension


__all__ = ["PLAYLIST_FILE_EXTENSIONS", "playlist_file_extension"]
