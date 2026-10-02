"""Immutable assistance scopes built from existing local models, never renderer facts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from xfinaudio.ai.connection_test import PROBE_MESSAGE
from xfinaudio.ai.privacy import redact_paths
from xfinaudio.ai.saved_assists import anonymize_saved_request, build_saved_descriptors
from xfinaudio.headless.common import BackendError
from xfinaudio.headless.serato_safety import source_identity
from xfinaudio.headless.serato_source import load_source
from xfinaudio.metadata.metadata_gaps import build_metadata_gap_report
from xfinaudio.metadata.tempo import is_valid_bpm
from xfinaudio.recommendation.scoring import bpm_difference_percent, effective_energy_delta

if TYPE_CHECKING:
    from xfinaudio.headless.backend import HeadlessBackend

SURFACES = frozenset({"library", "prep", "review", "saved", "editor", "metadata", "live", "connection"})
FREE_TEXT = frozenset({"library", "prep", "saved", "editor"})


@dataclass(frozen=True)
class AssistContext:
    surface: str
    selector: dict[str, Any]
    request: str
    revision: str
    disclosure: tuple[str, ...]
    data: dict[str, Any]


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def build_context(backend: HeadlessBackend, surface: str, selector: dict[str, Any], request: str) -> AssistContext:
    if (
        not isinstance(surface, str)
        or surface not in SURFACES
        or not isinstance(selector, dict)
        or not isinstance(request, str)
        or len(request) > 2000
        or "\x00" in request
    ):
        raise BackendError("invalid_params", "Choose a bounded assistance request")
    if surface in FREE_TEXT and not request.strip():
        raise BackendError("invalid_params", "Enter a request first")
    if surface not in FREE_TEXT and request != (PROBE_MESSAGE if surface == "connection" else ""):
        raise BackendError("invalid_params", "This explanation uses only its disclosed fixed request")
    expected = {
        "review": {"reviewId"},
        "editor": {"editId"},
        "live": {"sessionId", "revision"},
        "saved": {"playlistIds"},
    }.get(surface, set())
    if set(selector) != expected and not (surface == "saved" and not selector):
        raise BackendError("invalid_params", "Unexpected assistance context fields")
    records = backend._records() if surface != "connection" else []
    if not records and surface != "connection":
        raise BackendError("ai_context_unavailable", "Scan an authorized library first")
    paths = [record.path for record in records]
    request = redact_paths(request, paths)
    identities = []
    for record in records:
        try:
            identity = source_identity(Path(record.path))
        except (OSError, ValueError):
            identity = None
        identities.append([record.path, identity])
    revision_data: list[Any] = [surface, selector, [r.model_dump(mode="json") for r in records], identities]
    data: dict[str, Any] = {"records": records}
    disclosure: tuple[str, ...] = ()
    if surface in {"library", "prep"}:
        genres = sorted(
            {record.genre for record in records if record.genre and redact_paths(record.genre, paths) == record.genre}
        )
        if len(genres) > 256 or any(len(g) > 100 for g in genres):
            raise BackendError("ai_context_too_large", "The genre vocabulary exceeds the supported request scope")
        data["genres"] = genres
        disclosure = (
            "Tu solicitud sin rutas de archivos.",
            f"Vocabulario de {len(genres)} géneros y filtros o estrategias permitidas.",
            "No se envían audio ni listas de títulos.",
        )
    elif surface == "review":
        source = load_source(backend, {"kind": "review", "reviewId": selector["reviewId"]})
        if backend.review is None:
            raise BackendError("ai_context_unavailable", "Prepare a current review first")
        data.update(
            recommendation=backend.review.recommendation.model_copy(deep=True),
            readiness=backend.review.readiness_report.model_copy(deep=True),
        )
        revision_data.append(source.revision)
        disclosure = (
            "Títulos y artistas de la selección en su orden revisado.",
            "BPM, tonalidad, energía, transiciones y datos locales de calidad y preparación.",
            "No se envían rutas ni archivos de audio.",
        )
    elif surface == "editor":
        session = backend.editor._current(selector["editId"])
        revision_data.append([session.edit_id, session.revision])
        disclosure = (
            "Solo tu petición de edición, sin rutas.",
            "No se envían títulos, listas de pistas ni audio. La propuesta requiere previsualización local.",
        )
    elif surface == "saved":
        ids = selector.get("playlistIds", [str(item.id) for item in backend.playlists.list_summaries()])
        if (
            not isinstance(ids, list)
            or not 1 <= len(ids) <= 200
            or any(
                not isinstance(value, str) or not value.isascii() or not value.isdecimal() or not 1 <= len(value) <= 15
                for value in ids
            )
            or len(set(ids)) != len(ids)
        ):
            raise BackendError("ai_context_too_large", "Choose 1–200 distinct saved playlists")
        playlists = [backend.playlists.get_by_id(int(value)) for value in ids]
        if any(item is None for item in playlists):
            raise BackendError("ai_context_unavailable", "A saved playlist no longer exists")
        playlists = [item for item in playlists if item is not None]
        data["playlists"] = playlists
        data["descriptors"] = build_saved_descriptors(playlists, records)
        request = anonymize_saved_request(request, playlists)
        revision_data.append([[p.id, p.name, p.updated_at.isoformat(), p.track_paths] for p in playlists])
        disclosure = (
            f"Descriptores anónimos de {len(playlists)} playlists: cantidades, géneros, duración y rangos conocidos.",
            (
                "Tu petición sustituye nombres conocidos por identificadores temporales. "
                "No se envían títulos de pistas, rutas ni audio."
            ),
        )
    elif surface == "metadata":
        report = build_metadata_gap_report(records)
        if not report.incomplete_count:
            raise BackendError("ai_context_unavailable", "There are no required metadata gaps to explain")
        data["facts"] = [
            {
                "id": "m0",
                "track_count": len(records),
                "missing_bpm": report.gaps.bpm,
                "missing_key": report.gaps.camelot_key,
                "missing_energy": report.gaps.energy_level,
            }
        ]
        disclosure = (
            "Solo recuentos locales de pistas y campos requeridos ausentes.",
            "No hay una selección de pistas bloqueadas disponible; no se evalúa esa prioridad.",
            "No se envían títulos, artistas, rutas ni audio. La IA no completa etiquetas.",
        )
    elif surface == "live":
        status = backend.live.execute("live.status", {"sessionId": selector["sessionId"]})
        if type(selector["revision"]) is not int or status["revision"] != selector["revision"]:
            raise BackendError("stale_ai", "The Live step changed")
        session = backend.live.session
        assert session is not None
        current = next(track for track in session.recommendation.ordered_tracks if track.path == session.played[-1])
        ranked = backend.live._ranked(session)[:5]
        if not ranked:
            raise BackendError("ai_context_unavailable", "No current Live candidates to explain")
        data["facts"] = [
            {
                "id": f"c{i}",
                "rank": i + 1,
                "score": item.score.total_score,
                "bpm_delta": bpm_difference_percent(cast(float, current.bpm), cast(float, item.track.bpm))
                if is_valid_bpm(current.bpm) and is_valid_bpm(item.track.bpm)
                else None,
                "energy_delta": effective_energy_delta(current, item.track)[0]
                if (current.energy_out is not None and item.track.energy_in is not None)
                or (current.energy_level is not None and item.track.energy_level is not None)
                else None,
                "readiness": item.readiness.status,
            }
            for i, item in enumerate(ranked)
        ]
        revision_data.append([session.id, session.revision, session.source_revision, session.played, data["facts"]])
        disclosure = (
            "Candidatas anónimas, orden, puntuaciones y diferencias absolutas calculadas localmente.",
            "No se envían títulos, rutas ni audio. La IA no cambia el orden ni controla Serato.",
        )
    else:
        disclosure = ("Solo el mensaje técnico visible de prueba.", "No se envía ningún contenido de la biblioteca.")
    return AssistContext(surface, dict(selector), request, _fingerprint(revision_data), disclosure, data)


# Kept separate to bound the authority/context review slice.
from xfinaudio.headless.ai_execution import apply_context, execute_context  # noqa: E402,F401
