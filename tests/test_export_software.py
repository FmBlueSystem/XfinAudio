from __future__ import annotations

import pytest

from xfinaudio.exporting.software import playlist_file_extension


def test_playlist_file_extension_returns_existing_supported_extensions() -> None:
    assert playlist_file_extension("Rekordbox") == ".xml"
    assert playlist_file_extension("Traktor") == ".nml"
    assert playlist_file_extension("VirtualDJ") == ".xml"


def test_playlist_file_extension_rejects_unknown_software() -> None:
    with pytest.raises(ValueError, match="Unknown export software: Ableton"):
        playlist_file_extension("Ableton")
