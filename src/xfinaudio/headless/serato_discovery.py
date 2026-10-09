"""Automatic Serato destination discovery for the export flow (issue #366).

The desktop export flow must be able to locate a usable `_Serato_` folder
without showing a folder picker. Candidates, in order:

1. `_Serato_` directly under each scanned library root (the usual layout: the
   DJ library and Serato live on the same volume).
2. `<home>/Music/_Serato_`, only when it shares the library's single source
   volume — `serato.preview` blocks cross-volume destinations, so suggesting
   one that cannot be used would be dishonest.

A candidate is usable when its `Subcrates` directory exists, matching the
validation `serato.registerDestination` performs. Suggestions are always
canonical (resolved) paths so registration accepts them unchanged.
"""

from collections.abc import Callable, Sequence
from pathlib import Path

from xfinaudio.headless.serato_safety import volume_root

VolumeOf = Callable[[Path], object]


def _usable(candidate: Path) -> bool:
    return (candidate / "Subcrates").is_dir()


def suggest_destination(roots: Sequence[Path], *, home: Path, volume_of: VolumeOf = volume_root) -> Path | None:
    """Return the canonical `_Serato_` folder to offer first, or ``None``."""
    for root in roots:
        candidate = root / "_Serato_"
        if _usable(candidate):
            return candidate.resolve()
    home_candidate = home / "Music" / "_Serato_"
    if _usable(home_candidate) and (
        not roots
        or (len({volume_of(root) for root in roots}) == 1 and volume_of(home_candidate) == volume_of(roots[0]))
    ):
        return home_candidate.resolve()
    return None
