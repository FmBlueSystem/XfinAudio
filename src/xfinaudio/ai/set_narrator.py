"""Natural-language set narrative for the XfinAudio AI surface.

``narrate_set`` turns a finished recommendation plus its DJ readiness report
into a short, DJ-facing narrative of the set's arc.

Contract: the model is a narrator, never a source of truth. Every fact it may
repeat is derived from the two arguments (ordered tracks with BPM/key/energy,
per-transition warnings, the readiness summary, the total transition score and
the optimizer name) and is handed over in the user message. The model is
explicitly forbidden from inventing track names, numbers, or claims, so a set
with nothing to talk about (no ordered tracks) refuses with a ``ValueError``
before any request is built instead of asking the model to fill the silence.

Language: the narration is requested in rioplatense Spanish, because that is
the language the DJ reads in the Review screen and the text is shown verbatim
there. The service still just takes facts and returns the model text unchanged;
the language decision lives in the system prompt it builds, not in the caller.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from xfinaudio.ai.nan_client import ENABLED_ENV, NanConfigError, chat, is_ai_enabled
from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.dj_readiness import DjReadinessReport
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation

if TYPE_CHECKING:
    from xfinaudio.ai.nan_client import Transport

#: Narration is a reasoning call over a whole set, not a classification one.
#: The adapter's 30s default timed out on the slower Nan models, so this surface
#: allows two full minutes instead of exposing a timeout control.
DEFAULT_NARRATE_TIMEOUT_SECONDS = 120.0

#: Length guidance handed to the model. Kept as a bound, not a truncation: the
#: service never edits the text the model returns.
_MAX_WORDS = 150


def narrate_set(
    recommendation: PlaylistRecommendation,
    readiness: DjReadinessReport,
    *,
    model: str | None = None,
    timeout: float = DEFAULT_NARRATE_TIMEOUT_SECONDS,
    transport: Transport | None = None,
) -> str:
    """Narrate the recommended set's arc from engine facts, in rioplatense Spanish.

    The facts are built exclusively from *recommendation* and *readiness*: the
    ordered track list (index, title, artist, BPM, Camelot key, energy level),
    the warnings of each transition, the readiness status/summary/blocker/review
    counts, the total transition score, and the optimizer name. The model text is
    returned verbatim; the caller renders it as-is in the Review screen.

    Args:
        recommendation: The recommended set, in play order.
        readiness: The DJ readiness report for that same set.
        model: Optional model override forwarded to the adapter.
        timeout: Request timeout in seconds. Two minutes by default, because
            narrating a whole set is slower than the adapter's 30s default.
        transport: Injectable transport; tests pin it to stay offline.

    Raises:
        NanConfigError: when AI is not enabled via ``XFINAUDIO_AI_ENABLED``.
        ValueError: when the recommendation holds no ordered tracks, so there is
            nothing to narrate. Raised before the transport is reached.
        NanRequestError: when the request itself fails (HTTP or timeout). The
            adapter's messages stay bounded and never carry the API key.
    """
    if not is_ai_enabled():
        raise NanConfigError(
            f"AI is disabled: set {ENABLED_ENV}=1 in the environment before requesting a set narrative."
        )
    if not recommendation.ordered_tracks:
        raise ValueError("There is nothing to narrate: the recommendation holds no ordered tracks.")

    return chat(
        _build_facts(recommendation, readiness),
        system=_build_system_prompt(),
        model=model,
        timeout=timeout,
        transport=transport,
    )


def _build_system_prompt() -> str:
    return (
        "You are a DJ set analyst. You write a short narrative of a recommended set: "
        "how it opens, how it moves, and where it lands, for the DJ who will play it.\n"
        "Use ONLY the facts given in the user message. Never invent track names, "
        "artists, BPM values, keys, energy levels, transition counts, or any claim "
        f"that is not in those facts. If a fact is missing, leave it out.\n"
        f"Keep the answer under {_MAX_WORDS} words, in a single paragraph of plain "
        "text: no markdown, no headings, no lists.\n"
        "Write the narration in español rioplatense (voseo), because the DJ reads it "
        "verbatim in the Review screen."
    )


def _build_facts(recommendation: PlaylistRecommendation, readiness: DjReadinessReport) -> str:
    """Render the only source of truth the model may narrate from."""
    sections: list[str] = [
        "Set facts. These are the only facts you may use:\n",
        "Tracks in play order (index. title — artist | BPM | Camelot key | energy):",
        _track_lines(recommendation),
    ]

    warnings = _transition_warning_lines(recommendation)
    sections.append("\nTransition warnings:")
    sections.append("\n".join(warnings) if warnings else "- none")

    sections.append(
        "\nReadiness:\n"
        f"- status: {readiness.status}\n"
        f"- summary: {readiness.summary}\n"
        f"- blockers: {readiness.blocker_count}\n"
        f"- review items: {readiness.review_count}"
    )
    sections.append(f"\nTotal transition score: {recommendation.total_score:.2f}")
    sections.append(f"Optimizer: {recommendation.optimizer}")
    return "\n".join(sections)


def _track_lines(recommendation: PlaylistRecommendation) -> str:
    lines: list[str] = []
    for index, track in enumerate(recommendation.ordered_tracks, start=1):
        title = (track.title or "(untitled)").strip()
        artist = (track.artist or "(unknown artist)").strip()
        bpm = f"{track.bpm:g}" if track.bpm is not None else "unknown"
        camelot = (track.camelot_key or "unknown").strip()
        energy = str(track.energy_level) if track.energy_level is not None else "unknown"
        lines.append(f"{index}. {title} — {artist} | BPM {bpm} | {camelot} | energy {energy}")
    return "\n".join(lines)


def _transition_warning_lines(recommendation: PlaylistRecommendation) -> list[str]:
    """One line per transition that carries warnings; transitions without any are omitted."""
    ordered = recommendation.ordered_tracks
    lines: list[str] = []
    for index, transition in enumerate(recommendation.transition_scores, start=1):
        if not transition.warnings:
            continue
        left = _title_for_path(ordered, transition.left_path)
        right = _title_for_path(ordered, transition.right_path)
        lines.append(f"- Transition {index} ({left} -> {right}): {'; '.join(transition.warnings)}")
    return lines


def _title_for_path(ordered: list[TrackRecord], path: str) -> str:
    for track in ordered:
        if track.path == path:
            title = (track.title or "").strip()
            return title or track.path
    return path


__all__ = ["DEFAULT_NARRATE_TIMEOUT_SECONDS", "narrate_set"]
