"""Local saved-set retrieval and descriptive comparison from actual evidence."""

from __future__ import annotations

import math
import re
from collections.abc import Sequence

from xfinaudio.application.playlist_edit_intents import normalize_request
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_models import Playlist

_STOPWORDS = frozenset(
    "find show me my saved playlists playlist sets set with containing named called please "
    "busca buscar muestra mis listas lista guardadas guardados con de nombre canciones temas".split()
)


def search_saved_sets(request: str, playlists: Sequence[Playlist], records: Sequence[TrackRecord]) -> list[Playlist]:
    """Match all meaningful words and optional strict count/duration bounds."""
    text = normalize_request(request)
    bound = re.search(r"\b(under|over|menos de|mas de) (\d+) (tracks?|minutes?|minutos?|canciones?|temas?)\b", text)
    if bound:
        text = text[: bound.start()] + text[bound.end() :]
    words = set(re.findall(r"\w+", text)) - _STOPWORDS
    by_path = {r.path: r for r in records}
    results = []
    for playlist in playlists:
        tracks = [by_path[path] for path in playlist.track_paths if path in by_path]
        haystack = normalize_request(
            " ".join(
                [
                    playlist.name,
                    *(" ".join([r.title or "", r.artist or "", r.genre or "", *r.tags]) for r in tracks),
                ]
            )
        )
        if not all(word in haystack for word in words):
            continue
        if bound:
            value = float(len(playlist.track_paths))
            if bound[3] in {"minute", "minutes", "minuto", "minutos"}:
                durations = [_positive(r.duration) for r in tracks]
                if len(tracks) != len(playlist.track_paths) or any(d is None for d in durations):
                    continue
                value = sum(d for d in durations if d is not None) / 60
            limit = int(bound[2])
            if (bound[1] in {"under", "menos de"} and value >= limit) or (
                bound[1] in {"over", "mas de"} and value <= limit
            ):
                continue
        results.append(playlist)
    return results


def describe_saved_set(playlist: Playlist, records: Sequence[TrackRecord]) -> str:
    by_path = {r.path: r for r in records}
    tracks = [by_path[p] for p in playlist.track_paths if p in by_path]
    count = len(playlist.track_paths)
    energy = [r.energy_level for r in tracks if r.energy_level is not None]
    bpms = [b for r in tracks if (b := _positive(r.bpm)) is not None]
    durations = [d for r in tracks if (d := _positive(r.duration)) is not None]
    energy_text = f"energy {sum(energy) / len(energy):.1f}" if energy else "energy unknown"
    bpm_text = f"BPM {min(bpms):g}–{max(bpms):g}" if bpms else "BPM unknown"
    duration_text = f"duration {sum(durations) / 60:.1f} min" if len(durations) == count else "duration unknown"
    return (
        f"{playlist.name}: {count} tracks; {energy_text} ({len(energy)}/{count} known); "
        f"{bpm_text} ({len(bpms)}/{count} known); {duration_text} ({len(durations)}/{count} known)"
    )


def compare_saved_sets(playlists: Sequence[Playlist], records: Sequence[TrackRecord]) -> str:
    if len(playlists) < 2:
        raise ValueError("Select at least two saved playlists to compare.")
    descriptions = [describe_saved_set(p, records) for p in playlists]
    shared = set(playlists[0].track_paths).intersection(*(set(p.track_paths) for p in playlists[1:]))
    return "\n".join([*descriptions, f"{len(shared)} shared unique track(s) across these saved sets."])


def _positive(value: float | None) -> float | None:
    return value if value is not None and math.isfinite(value) and value > 0 else None
