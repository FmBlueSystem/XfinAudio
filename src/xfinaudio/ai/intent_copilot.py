"""Natural-language intent copilot for the XfinAudio AI surface.

``extract_intent`` turns a DJ's free-form set request into a validated,
vocabulary-normalized :class:`~xfinaudio.recommendation.prep_copilot.DJSetIntent`.

Contract: the LLM only fills the intent struct. It never selects or orders
tracks; track selection and ordering always belong to the deterministic engine
(``build_prep_copilot_plan``). Everything the LLM returns is treated as an
untrusted suggestion and is normalized against the local library before use.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from xfinaudio.ai.nan_client import ENABLED_ENV, NanConfigError, chat, is_ai_enabled
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.prep_copilot import DJSetIntent
from xfinaudio.recommendation.strategies import available_strategies

if TYPE_CHECKING:
    from xfinaudio.ai.nan_client import Transport

#: Fallback strategy when the LLM names something the engine cannot resolve.
_STRATEGY_FALLBACK = "harmonic_journey"

#: The slot-role arcs the engine can render, decoupled from the ordering strategy.
_SLOT_ROLES = ("warmup", "peak_time", "chill")

#: Upper bound on how much of the raw LLM response an error may echo. Keeps the
#: message bounded and keeps a stray key out of any user-visible error.
_MAX_RAW_ECHO = 200

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)
_SEPARATOR = re.compile(r"[\s_-]+")


def extract_intent(
    user_request: str,
    tracks: list[TrackRecord],
    *,
    model: str | None = None,
    timeout: float = 60.0,
    transport: Transport | None = None,
    genre_vocabulary: list[str] | None = None,
) -> DJSetIntent:
    """Translate a natural-language DJ request into a validated ``DJSetIntent``.

    The LLM only fills the intent fields; the deterministic engine owns track
    selection and ordering. The model's free-form strings are normalized against
    the provided library: ``genre_focus`` is mapped to the library's exact
    casing (or an explicit ``genre_vocabulary`` override), ``strategy`` is
    validated against :func:`available_strategies` with a ``harmonic_journey``
    fallback, ``slot_role`` is matched case/space-insensitively to the known role
    names (or ``None`` when unknown), and ``start_title``/``end_title`` are
    resolved to track paths by case-insensitive title match (unmatched titles drop
    the path rather than inventing one). ``target_minutes`` is left to the
    ``DJSetIntent`` field validators, which coerce a numeric value and enforce the
    ``gt=0``/``le=600`` bounds.

    Raises:
        NanConfigError: when AI is not enabled via ``XFINAUDIO_AI_ENABLED``.
        ValueError: when the model does not return a JSON object matching
            ``DJSetIntent``. The message is bounded and never carries the API
            key or the full raw response.
    """
    if not is_ai_enabled():
        raise NanConfigError(
            f"AI is disabled: set {ENABLED_ENV}=1 in the environment before requesting a copilot intent."
        )

    strategy_names = [str(name) for name in available_strategies()]
    genres = _genre_vocabulary(tracks, genre_vocabulary)
    raw = chat(
        _build_user_message(user_request, tracks, genres),
        system=_build_system_prompt(strategy_names),
        model=model,
        timeout=timeout,
        transport=transport,
    )

    data = _extract_json_object(raw)
    raw_start = data.pop("start_title", None)
    raw_end = data.pop("end_title", None)
    raw_slot_role = data.pop("slot_role", None)
    try:
        intent = DJSetIntent.model_validate(data)
    except ValidationError:
        raise ValueError(f"LLM JSON did not match the DJSetIntent schema: {_snippet(raw)!r}.") from None

    title_lookup = _title_lookup(tracks)
    return intent.model_copy(
        update={
            "genre_focus": _normalize_genre(intent.genre_focus, genres),
            "strategy": _normalize_strategy(intent.strategy, strategy_names),
            "slot_role": _normalize_slot_role(raw_slot_role),
            "start_path": _match_title(raw_start, title_lookup),
            "end_path": _match_title(raw_end, title_lookup),
        }
    )


def _build_system_prompt(strategy_names: list[str]) -> str:
    return (
        "You translate a DJ's natural-language set request into JSON for the "
        "XfinAudio DJSetIntent model. Respond with ONLY a JSON object: no markdown "
        "and no prose.\n"
        f"Allowed strategy values: {json.dumps(strategy_names)}.\n"
        'Schema: {"name": string, "strategy": string, "target_track_count": integer '
        'between 2 and 100, "target_minutes": number between 5 and 600 or null, '
        '"slot_role": one of ["warmup", "peak_time", "chill"] or null, '
        '"genre_focus": string or null, "start_title": string or '
        'null, "end_title": string or null}.\n'
        "target_minutes is the number of minutes the set must fill; use it only "
        "when the DJ's request states or clearly implies a set length in time "
        "(minutes or hours), else null.\n"
        "slot_role is the arc curve for the set's role in the night; use it only "
        "when the DJ's request describes the set's role (for example an opening "
        "set, a closing set or peak time), not when it only describes the music's "
        "shape, else null. It is independent of the ordering strategy.\n"
        "genre_focus must be copied verbatim from the library genre vocabulary.\n"
        "start_title and end_title, when present, must match a title in the track "
        "list exactly; otherwise use null.\n"
        "You only fill the intent fields. Never select or order tracks: track "
        "selection belongs to the deterministic engine."
    )


def _build_user_message(user_request: str, tracks: list[TrackRecord], genres: list[str]) -> str:
    return (
        f"DJ request:\n{user_request}\n\n"
        f"Library genre vocabulary (use this exact casing): {json.dumps(genres)}\n\n"
        "Available tracks (title | genre):\n"
        f"{_compact_track_list(tracks)}"
    )


def _compact_track_list(tracks: list[TrackRecord]) -> str:
    lines = []
    for track in tracks:
        title = (track.title or "(untitled)").strip()
        genre = (track.genre or "(unknown genre)").strip()
        lines.append(f"- {title} | {genre}")
    return "\n".join(lines)


def _genre_vocabulary(tracks: list[TrackRecord], override: list[str] | None) -> list[str]:
    """Return the genre vocabulary: an explicit override, else the library's genres."""
    if override is not None:
        return list(override)
    vocabulary: list[str] = []
    seen: set[str] = set()
    for track in tracks:
        genre = (track.genre or "").strip()
        key = genre.casefold()
        if genre and key not in seen:
            seen.add(key)
            vocabulary.append(genre)
    return vocabulary


def _normalize_genre(value: str | None, vocabulary: list[str]) -> str | None:
    """Map a free-form genre onto the vocabulary's exact casing, else ``None``."""
    if value is None:
        return None
    lookup: dict[str, str] = {}
    for genre in vocabulary:
        canonical = genre.strip()
        if canonical:
            lookup.setdefault(canonical.casefold(), canonical)
    return lookup.get(value.strip().casefold())


def _normalize_strategy(value: str, allowed: list[str]) -> str:
    """Match the LLM's strategy case-insensitively, falling back to harmonic_journey."""
    lookup = {_SEPARATOR.sub("_", name.strip().casefold()): name for name in allowed}
    return lookup.get(_SEPARATOR.sub("_", value.strip().casefold()), _STRATEGY_FALLBACK)


def _normalize_slot_role(value: object) -> str | None:
    """Match the LLM's slot role case/space-insensitively, else ``None``.

    Mirrors :func:`_normalize_strategy`'s separator handling. An unknown or
    non-string role maps to ``None`` rather than guessing, so the engine keeps its
    legacy strategy-coupled curve.
    """
    if not isinstance(value, str):
        return None
    lookup = {_SEPARATOR.sub("_", role): role for role in _SLOT_ROLES}
    return lookup.get(_SEPARATOR.sub("_", value.strip().casefold()))


def _title_lookup(tracks: list[TrackRecord]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for track in tracks:
        title = (track.title or "").strip()
        if title:
            lookup.setdefault(title.casefold(), track.path)
    return lookup


def _match_title(value: object, lookup: dict[str, str]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return lookup.get(value.strip().casefold())


def _extract_json_object(raw: str) -> dict[str, Any]:
    """Return the first ``{...}`` block decoded as an object, else raise ValueError."""
    match = _JSON_BLOCK.search(raw)
    if match is None:
        raise ValueError(f"LLM did not return a JSON object: {_snippet(raw)!r}.")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        raise ValueError(f"LLM did not return a JSON object: {_snippet(raw)!r}.") from None
    if not isinstance(data, dict):
        raise ValueError(f"LLM did not return a JSON object: {_snippet(raw)!r}.")
    return data


def _snippet(raw: str, limit: int = _MAX_RAW_ECHO) -> str:
    """Bound how much raw model output is echoed in an error message."""
    text = raw.strip()
    return text[:limit] + "..." if len(text) > limit else text
