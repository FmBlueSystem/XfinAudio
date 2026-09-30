"""Bounded offline language interpretation and deterministic draft validation."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from collections.abc import Collection, Sequence

from xfinaudio.library.models import TrackRecord


def normalize_request(text: str) -> str:
    return " ".join(
        "".join(c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c)).split()
    ).strip(" .!?")


def validate_edit(
    source: Sequence[str],
    candidate: Sequence[str],
    *,
    locked_paths: Collection[str] = (),
    excluded_paths: Collection[str] = (),
) -> None:
    """Reject invented paths, duplicate additions and violated source constraints."""
    before, after = Counter(source), Counter(candidate)
    if after - before:
        raise ValueError("A draft cannot add unknown or duplicate tracks.")
    if set(candidate) & set(excluded_paths):
        raise ValueError("Remove excluded tracks before saving this draft.")
    if set(source) & set(locked_paths) & set(excluded_paths):
        raise ValueError("A track is both locked and excluded; resolve the conflicting controls.")
    if any(after[path] != before[path] for path in set(source) & set(locked_paths)):
        raise ValueError("The edit would remove a locked track.")


def propose_edit(
    request: str,
    paths: Sequence[str],
    records: Sequence[TrackRecord],
    *,
    locked_paths: Collection[str] = (),
    excluded_paths: Collection[str] = (),
) -> tuple[str, ...]:
    """Return a validated proposal; never modify records, paths or storage."""
    locked, excluded = set(locked_paths), set(excluded_paths)
    if set(paths) & locked & excluded:
        raise ValueError("A track is both locked and excluded; resolve the conflicting controls.")
    source = [p for p in paths if p not in excluded]
    text = normalize_request(request)
    if text in {"hazlo mas corto", "make it shorter", "shorten it"}:
        raise ValueError("Choose a target: 'acorta a 10 temas' / 'shorten to 10 tracks' / 'shorten to 30 minutes'.")
    count = re.fullmatch(
        r"(?:shorten(?: this (?:set|playlist))? to|acorta(?: este set)? a) (\d+) "
        r"(tracks?|canciones?|temas?|minutes?|minutos?)",
        text,
    )
    if count:
        target = int(count[1])
        if target < 1:
            raise ValueError("Choose a positive shortening target.")
        result = _shorten(source, records, locked, target, count[2] in {"minute", "minutes", "minuto", "minutos"})
    elif text in {
        "raise energy",
        "increase energy",
        "rising energy",
        "sube la energia",
        "sube gradualmente la energia",
        "lower energy",
        "falling energy",
        "baja la energia",
        "baja gradualmente la energia",
    }:
        by_path = {record.path: record for record in records}
        movable = [p for p in source if p not in locked]
        if any(p not in by_path or by_path[p].energy_level is None for p in movable):
            raise ValueError("Known energy metadata is required for every unlocked track.")
        descending = text in {"lower energy", "falling energy", "baja la energia", "baja gradualmente la energia"}
        ordered = iter(sorted(movable, key=lambda p: by_path[p].energy_level or 0, reverse=descending))
        result = [p if p in locked else next(ordered) for p in source]
    else:
        raise ValueError("Try 'shorten to 10 tracks', 'shorten to 30 minutes', 'raise energy' or 'lower energy'.")
    validate_edit(paths, result, locked_paths=locked, excluded_paths=excluded)
    return tuple(result)


def _shorten(
    source: list[str], records: Sequence[TrackRecord], locked: set[str], target: int, minutes: bool
) -> list[str]:
    weights = dict.fromkeys(source, 1.0)
    limit = float(target)
    if minutes:
        durations = {r.path: r.duration for r in records}
        for path in source:
            duration = durations.get(path)
            if duration is None or not math.isfinite(duration) or duration <= 0:
                raise ValueError("Known positive duration metadata is required for every track.")
            weights[path] = duration
        limit *= 60
    result = list(source)
    total = sum(weights[p] for p in result)
    for index in range(len(result) - 1, -1, -1):
        if total <= limit:
            break
        path = result[index]
        if path not in locked:
            total -= weights[path]
            result.pop(index)
    if total > limit:
        raise ValueError("The target cannot be reached without removing locked tracks.")
    return result
