"""Minimize outbound text without changing local metadata or musical intent."""

from __future__ import annotations

import re
from collections.abc import Iterable

_MARKER = "[private path]"
_PREFIX = (
    r"(?:file://[^\s]*?/|[A-Za-z]:[\\/]|\\\\|~[/\\]|\.{1,2}[/\\]|"
    r"/(?:Users|home|Volumes|private|tmp|mnt|media)/|(?<!\w)/)"
)
_QUOTED = re.compile(r"([\"'])" + _PREFIX + r".*?\1")
# Audio filenames may contain spaces; consume through the suffix before the
# generic token pass. Known complete paths are always replaced first.
_AUDIO_PATH = re.compile(_PREFIX + r"[^\n\r\"'<>|;]*?\.(?:mp3|wav|aiff?|flac|m4a|aac|ogg|opus)\b", re.IGNORECASE)
_PATH_TOKEN = re.compile(_PREFIX + r"[^\s\"'<>|;,)}\]]+")
_AUDIO_SUFFIX = r"\.(?:mp3|wav|aiff?|flac|m4a|aac|ogg|opus)\b"
_RELATIVE_QUOTED_AUDIO = re.compile(
    r"([\"'])[^\n\r\"'<>|]*?[/\\][^\n\r\"'<>|]*?" + _AUDIO_SUFFIX + r"\1", re.IGNORECASE
)
# Unquoted directory components must be whitespace-free; quoted paths above
# support spaces throughout. Do not consume earlier genre/ratio prose as a path.
_RELATIVE_AUDIO = re.compile(
    r"(?<![\w/\\])(?:[^\s/\\\"'<>|;,(){}\[\]:]+[/\\])+"
    r"[^/\\\n\r\"'<>|;]*?" + _AUDIO_SUFFIX,
    re.IGNORECASE,
)


def redact_paths(text: str, known_paths: Iterable[str] = ()) -> str:
    """Replace known paths and recognizable POSIX/Windows paths in free text.

    Keep ordinary slash-containing genre names and numeric ratios intact. This
    is defense-in-depth, not an invitation to share arbitrary raw metadata.
    """
    for path in sorted(set(known_paths), key=len, reverse=True):
        if path:
            pattern = re.escape(path)
            if not any(char in path for char in ("/", "\\", ".")):
                pattern = r"(?<!\w)" + pattern + r"(?!\w)"
            text = re.sub(pattern, lambda _: _MARKER, text, flags=re.IGNORECASE)
    text = _RELATIVE_QUOTED_AUDIO.sub(lambda match: match[1] + _MARKER + match[1], text)
    text = _QUOTED.sub(lambda match: match[1] + _MARKER + match[1], text)
    text = _AUDIO_PATH.sub(_MARKER, text)
    text = _RELATIVE_AUDIO.sub(_MARKER, text)
    return _PATH_TOKEN.sub(_MARKER, text)
