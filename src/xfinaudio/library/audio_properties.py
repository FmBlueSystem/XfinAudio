"""Parser-confirmed stream facts; no suffix guesses, decoding or file writes."""

from __future__ import annotations

import math
from typing import Any

from mutagen.aiff import AIFF
from mutagen.flac import FLAC
from mutagen.mp3 import MP3, BitrateMode
from mutagen.mp4 import MP4
from mutagen.wave import WAVE


def stream_properties(audio: Any) -> dict[str, Any]:
    """Read declared header bitrate, which is not a measured encoded-file average."""
    properties: dict[str, Any] = {}
    info = getattr(audio, "info", None)
    for kind, name in ((FLAC, "FLAC"), (MP3, "MP3"), (WAVE, "WAV"), (AIFF, "AIFF"), (MP4, "MP4")):
        if isinstance(audio, kind):
            properties["audio_format"] = name
            break
    if isinstance(audio, MP3):
        if getattr(info, "layer", None) != 3:
            properties["audio_format"] = "MPEG Audio"
        mode = getattr(info, "bitrate_mode", None)
        properties["bitrate_mode"] = {BitrateMode.CBR: "CBR", BitrateMode.VBR: "VBR", BitrateMode.ABR: "ABR"}.get(mode)
    if isinstance(audio, MP4):
        properties["audio_codec"] = getattr(info, "codec_description", None) or getattr(info, "codec", None) or None
    bitrate = getattr(info, "bitrate", None)
    if isinstance(bitrate, (int, float)) and not isinstance(bitrate, bool) and math.isfinite(bitrate) and bitrate > 0:
        properties["bitrate_kbps"] = bitrate / 1000
    return properties
