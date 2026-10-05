"""Run original language services; explicit Apply produces only local UI suggestions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, cast

from xfinaudio.ai import nan_client
from xfinaudio.ai.connection_test import PROBE_MESSAGE
from xfinaudio.ai.grounded_evidence import explain_grounded_evidence
from xfinaudio.ai.intent_copilot import extract_intent
from xfinaudio.ai.saved_assists import interpret_saved_request
from xfinaudio.ai.set_narrator import narrate_set
from xfinaudio.ai.structured_assists import (
    interpret_editor_request,
    interpret_improvement_request,
    interpret_library_query,
)
from xfinaudio.application.library_query import LibraryQuery
from xfinaudio.application.playlist_edit_assessment import assess_playlist_edit
from xfinaudio.application.playlist_improvement import ImprovementError, validate_improvement_proposal
from xfinaudio.application.saved_playlist_assistant import compare_saved_sets
from xfinaudio.headless.ai_protocol import AI_REQUEST_TIMEOUT_SECONDS
from xfinaudio.headless.common import BackendError, _public_track, _text
from xfinaudio.headless.prep import make_intent

if TYPE_CHECKING:
    from xfinaudio.headless.ai_context import AssistContext
    from xfinaudio.headless.backend import HeadlessBackend


def execute_context(context: AssistContext, transport: nan_client.Transport) -> dict[str, Any]:
    surface, data = context.surface, context.data
    proposal = None
    text = ""
    kind = "commentary"
    if surface == "library":
        query = interpret_library_query(context.request, data["genres"], transport=transport)
        proposal = query.model_dump(mode="json")
        kind = "filters"
        text = query.interpretation_note
    elif surface == "prep":
        records = data["records"]
        intent = extract_intent(
            context.request,
            records,
            transport=transport,
            timeout=AI_REQUEST_TIMEOUT_SECONDS[surface],
            genre_vocabulary=data["genres"],
            include_track_titles=False,
        )
        proposal = {
            "name": _text(intent.name, "playlist name"),
            "targetTrackCount": intent.target_track_count,
            "strategy": intent.strategy,
        }
        for field, value in [
            ("targetMinutes", intent.target_minutes),
            ("genreFocus", intent.genre_focus),
            ("slotRole", intent.slot_role),
        ]:
            if value is not None:
                proposal[field] = value
        by_path = {record.path: _public_track(record)["id"] for record in records}
        for field, value in [("startTrackId", intent.start_path), ("endTrackId", intent.end_path)]:
            if value is not None:
                proposal[field] = by_path[value]
        if type(intent.target_track_count) is not int or not 2 <= intent.target_track_count <= 100:
            raise ValueError("Intent count outside local controls")
        make_intent(proposal, intent.name, {value: key for key, value in by_path.items()}, records)
        kind = "intent"
        text = "Propuesta de intención. El motor local seguirá eligiendo y ordenando las pistas."
    elif surface == "editor":
        candidates = data.get("candidates")
        if candidates is None:
            interpreted = interpret_editor_request(context.request, transport=transport)
            proposal = {"request": interpreted.command}
            kind = "editor_request"
            text = "Revisa esta petición en la previsualización local antes de aplicar y guardar."
        else:
            # Improvement responses reference only the prepare-time token snapshot; a path,
            # stable id, or out-of-scope token never reaches a local edit.
            improvement = interpret_improvement_request(context.request, candidates, transport=transport)
            proposal = {"orderedTrackIds": list(improvement.orderedTrackIds), "rationale": improvement.rationale}
            kind = "improvement"
            text = "Revisa el orden propuesto y su evaluación local antes de aplicarlo al borrador."
    elif surface == "saved":
        interpreted = interpret_saved_request(context.request, data["descriptors"], transport=transport)
        selected = [data["playlists"][int(value[1:])] for value in interpreted.selected_ids]
        proposal = {"action": interpreted.action, "playlistIds": [str(item.id) for item in selected]}
        kind = "saved_selection"
        text = "La comparación o selección se calculará localmente al aplicar."
    elif surface == "review":
        text = narrate_set(
            data["recommendation"], data["readiness"], transport=transport, timeout=AI_REQUEST_TIMEOUT_SECONDS[surface]
        )
    elif surface in {"metadata", "live"}:
        text = explain_grounded_evidence(
            cast(Literal["metadata", "live"], surface), data["facts"], transport=transport, timeout=30
        )
    else:
        value = nan_client.chat(PROBE_MESSAGE, transport=transport, timeout=10)
        if not value.strip():
            raise ValueError("Empty provider probe")
        kind = "connection"
        text = "La conexión respondió. No se envió contenido de la biblioteca."
    return {
        "surface": surface,
        "kind": kind,
        "title": "Sugerencia de IA opcional" if proposal is not None else "Comentario de IA opcional",
        "text": text,
        "proposal": proposal,
        "canApply": proposal is not None,
    }


def apply_context(backend: HeadlessBackend, context: AssistContext, answer: dict[str, Any]) -> dict[str, Any]:
    proposal = answer.get("proposal")
    if not answer.get("canApply") or not isinstance(proposal, dict):
        raise BackendError("invalid_params", "This commentary cannot apply actions")
    surface = context.surface
    if surface == "library":
        query = LibraryQuery.model_validate(proposal)
        data = {
            "filters": proposal,
            "trackIds": [_public_track(record)["id"] for record in context.data["records"] if query.matches(record)],
        }
    elif surface == "saved":
        ids = set(proposal["playlistIds"])
        selected = [item for item in context.data["playlists"] if str(item.id) in ids]
        data = {
            **proposal,
            "comparison": compare_saved_sets(selected, context.data["records"])
            if proposal["action"] == "compare"
            else "",
            "names": [item.name for item in selected],
        }
    elif surface == "editor" and "candidates" in context.data:
        data = _improvement_preview(backend, context, proposal)
    else:
        data = dict(proposal)
    return {"surface": surface, "data": data}


def _improvement_preview(backend: HeadlessBackend, context: AssistContext, proposal: dict[str, Any]) -> dict[str, Any]:
    """Bind the validated token order locally and return a path-free before/after preview.

    The order is re-validated against the prepare-time candidate snapshot, not the
    provider text, through the same local validator the binding uses. Everything that
    can fail -- order validation, assessment, and the before/after render -- is computed
    first; binding the session is the final step, so a failure never leaves a bound
    proposal that no successful preview ever returned. The binding is in session memory
    only: nothing is saved to the library, and no audio file is touched.
    """
    candidates = context.data["candidates"]
    ordered_tokens = proposal.get("orderedTrackIds")
    try:
        after_paths = validate_improvement_proposal(
            candidates.draft_tokens, candidates.paths_by_token, ordered_tokens if ordered_tokens is not None else ()
        )
    except ImprovementError as exc:
        raise BackendError(exc.code, str(exc)) from exc
    before_paths = tuple(candidates.paths_by_token[token] for token in candidates.draft_tokens)
    records = backend._records()
    try:
        assessment = assess_playlist_edit(after_paths, records)
    except ValueError as exc:
        raise BackendError("invalid_edit", str(exc)) from exc
    before = backend.editor._tracks(list(before_paths))
    after = backend.editor._tracks(list(after_paths))
    before_ids = [track["id"] for track in before]
    after_ids = [track["id"] for track in after]
    preview = {
        "before": before,
        "after": after,
        "assessment": {
            "description": assessment.description,
            "readiness": assessment.readiness.status,
            "qualityScore": assessment.quality.average_transition_score,
            "warnings": [check.detail for check in assessment.readiness.checks if check.status != "ready"]
            + [warning for score in assessment.recommendation.transition_scores for warning in score.warnings],
        },
        "addedIds": [track_id for track_id in after_ids if track_id not in set(before_ids)],
        "removedIds": [track_id for track_id in before_ids if track_id not in set(after_ids)],
    }
    bound = backend.editor.bind_improvement_proposal(
        context.selector["editId"],
        candidates,
        ordered_tokens,
        draft_ids=context.selector["draftIds"],
    )
    return {
        "proposalId": bound.proposal_id,
        "digest": bound.digest,
        "sourceRevision": bound.source_revision,
        **preview,
    }
