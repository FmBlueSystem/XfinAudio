"""The assistant's proposed list changes: kept in memory, published without identities, applied as edits.

The assistant never changes the list by itself. One successful chat turn may propose
up to twenty changes; the core binds each one to the track it named (never to its
position), resolves the library reference an ``add`` or a ``replace_with`` names
inside this conversation, computes the replacement a ``replace`` would use and keeps
the result next to the conversation, in memory only. The DJ applies one on request,
and that apply goes through exactly the code a manual review edit uses: a new revision,
undoable and stored like any other edit. Applying never contacts the provider.

Nothing published here carries a file path or a track identity: the answer names a
position, the title and artist of the track, and, for a library track, its fields.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from xfinaudio.ai.list_chat import MAX_TARGET_TRACK_COUNT
from xfinaudio.headless.ai_conversation import ChatAction, ConversationStore, applied_changes
from xfinaudio.headless.common import BackendError, _public_track
from xfinaudio.recommendation.playlist_service import in_year_range, insertion_positions

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from xfinaudio.application.prep_copilot import PrepCopilotVariantApplicationResult
    from xfinaudio.headless.backend import HeadlessBackend

_STALE = "Apply a change that is still pending and still possible"
#: Why a proposal could not be bound to the list; the opt-in chat log repeats it verbatim.
_NO_LIST = "no current list"
_TRACK_LEFT = "track left the list"
_NO_REPLACEMENT = "no replacement offered"
_SAME_VARIANT = "the list already uses that alternative"
_NO_VARIANT = "no such alternative in the plan"
_UNKNOWN_REFERENCE = "unknown library reference"
_PROTECTED_SLOT = "protected insert position"
_FULL = "the list is already at its track limit"
_NOTHING_TO_UNDO = "nothing to undo in this list"
_NOTHING_OUTSIDE = "no track outside the period"


def propose_actions(
    backend: HeadlessBackend, review_id: str, items: Sequence[Mapping[str, Any]]
) -> tuple[tuple[ChatAction, ...], tuple[tuple[Mapping[str, Any], str], ...]]:
    """Bind this turn's validated proposals to what they named.

    ``items`` is the parsed answer's own shape (``type``, ``reason`` and, depending on
    the type, ``position``, ``to``, ``ref``, ``order``, ``yearMin`` or ``yearMax``). A
    proposal whose track is no longer in the list, whose ``ref`` this conversation never
    issued, whose ``add`` has no free insert slot, whose ``replace`` has no replacement
    the engine still offers, whose ``use_variant`` names the alternative already in use
    or whose ``period`` would replace nothing is dropped and counted instead of failing
    the turn; it is returned with the reason it was dropped for the opt-in chat log. A
    ``reorder`` and an ``undo`` are bound to the tracks and to the revision's own
    history, so a later edit makes them stale instead of wrong.
    """
    review, plan = backend.review, backend.plan
    if review is None or plan is None:
        return (), tuple((item, _NO_LIST) for item in items)
    store = backend.ai_conversation
    tracks = list(review.recommendation.ordered_tracks)
    allowed_slots = insertion_positions(review.recommendation, frozenset(plan.intent.required_paths))
    accepted: list[ChatAction] = []
    dropped: list[tuple[Mapping[str, Any], str]] = []
    for item in items:
        kind, reason = item["type"], item["reason"]
        if kind == "extend":
            accepted.append(ChatAction(str(uuid4()), "extend", None, item["to"], reason))
            continue
        if kind == "period":
            # A period changes nothing when every track the fit could touch is already
            # inside the range, so it is never offered as a change.
            if not _outside_period(backend, review, item["yearMin"], item["yearMax"]):
                dropped.append((item, _NOTHING_OUTSIDE))
                continue
            accepted.append(
                ChatAction(
                    str(uuid4()),
                    "period",
                    None,
                    None,
                    reason,
                    year_min=item["yearMin"],
                    year_max=item["yearMax"],
                )
            )
            continue
        if kind == "use_variant":
            track_count, refusal = _offered_variant(backend, review.variant_name, item["variant"])
            if track_count is None:
                dropped.append((item, refusal))
                continue
            accepted.append(
                ChatAction(
                    str(uuid4()), "use_variant", None, None, reason, variant=item["variant"], track_count=track_count
                )
            )
            continue
        if kind == "undo":
            if not backend.review_actions.details()["canUndo"]:
                dropped.append((item, _NOTHING_TO_UNDO))
                continue
            accepted.append(ChatAction(str(uuid4()), "undo", None, None, reason))
            continue
        if kind == "reorder":
            order = tuple(_public_track(tracks[position - 1])["id"] for position in item["order"])
            accepted.append(ChatAction(str(uuid4()), "reorder", None, None, reason, order=order))
            continue
        if kind == "add":
            entering, refusal = _referenced(backend, store, review, item["ref"])
            if entering is None:
                dropped.append((item, refusal))
                continue
            if len(tracks) >= MAX_TARGET_TRACK_COUNT:
                dropped.append((item, _FULL))
                continue
            if item["position"] not in allowed_slots:
                dropped.append((item, _PROTECTED_SLOT))
                continue
            accepted.append(
                ChatAction(str(uuid4()), "add", None, None, reason, replacement_id=entering, position=item["position"])
            )
            continue
        position = item["position"]
        if not 1 <= position <= len(tracks):
            dropped.append((item, _TRACK_LEFT))
            continue
        track_id = _public_track(tracks[position - 1])["id"]
        if kind == "remove":
            accepted.append(ChatAction(str(uuid4()), "remove", track_id, None, reason))
            continue
        if kind == "replace_with":
            replacement_id, refusal = _referenced(backend, store, review, item["ref"])
            if replacement_id is None:
                dropped.append((item, refusal))
                continue
            accepted.append(
                ChatAction(str(uuid4()), "replace_with", track_id, None, reason, replacement_id=replacement_id)
            )
            continue
        if kind == "move":
            accepted.append(ChatAction(str(uuid4()), "move", track_id, item["to"], reason))
            continue
        replacement = _offered_replacement(backend, review_id, track_id)
        if replacement is None:
            dropped.append((item, _NO_REPLACEMENT))
            continue
        accepted.append(ChatAction(str(uuid4()), "replace", track_id, None, reason, replacement["id"]))
    return tuple(accepted), tuple(dropped)


def _referenced(
    backend: HeadlessBackend, store: ConversationStore, review: PrepCopilotVariantApplicationResult, reference: Any
) -> tuple[str | None, str]:
    """The library track one conversation reference names, or why it cannot join the list.

    The reference must be one this conversation issued, and the track behind it must
    still pass the review's own insert rule: complete metadata, not in the list and not
    excluded by the plan.
    """
    track_id = store.referenced(reference) if isinstance(reference, str) else None
    if track_id is None:
        return None, _UNKNOWN_REFERENCE
    try:
        backend.review_actions._entering(review, track_id)
    except BackendError as error:
        return None, str(error)
    return track_id, ""


def public_actions(backend: HeadlessBackend, actions: Iterable[ChatAction]) -> list[dict[str, Any]]:
    """The pending changes as the DJ sees them, at their current positions.

    A change whose track left the list, whose library track is no longer in the
    library or whose bound order no longer describes this list is not offered: it
    cannot apply any more. Only the stored library records are consulted here, so
    publishing never re-reads the library from disk.
    """
    review = backend.review
    if review is None:
        return []
    tracks = [_public_track(track) for track in review.recommendation.ordered_tracks]
    current_ids = [track["id"] for track in tracks]
    positions = {track["id"]: index for index, track in enumerate(tracks, start=1)}
    records = (_public_track(record) for record in backend._records(checked=frozenset()))
    library = {track["id"]: track for track in records}
    published: list[dict[str, Any]] = []
    for action in actions:
        if action.type == "extend":
            if action.to is None:
                continue
            published.append({"actionId": action.id, "type": "extend", "to": action.to, "reason": action.reason})
            continue
        if action.type == "use_variant":
            if action.variant is None or action.track_count is None:
                continue
            published.append(
                {
                    "actionId": action.id,
                    "type": "use_variant",
                    "variant": action.variant,
                    "trackCount": action.track_count,
                    "reason": action.reason,
                }
            )
            continue
        if action.type == "undo":
            published.append({"actionId": action.id, "type": "undo", "reason": action.reason})
            continue
        if action.type == "period":
            if action.year_min is None or action.year_max is None:
                continue
            outside = _outside_period(backend, review, action.year_min, action.year_max)
            if not outside:
                # Nothing is left outside the range: this change has nothing to offer.
                continue
            published.append(
                {
                    "actionId": action.id,
                    "type": "period",
                    "yearMin": action.year_min,
                    "yearMax": action.year_max,
                    "outside": outside,
                    "reason": action.reason,
                }
            )
            continue
        if action.type == "reorder":
            order = action.order
            if order is None or sorted(order) != sorted(current_ids):
                continue
            moved = sum(1 for index, track_id in enumerate(order) if track_id != current_ids[index])
            if moved == 0:
                # Nothing would change place (an identity order, or one already applied).
                continue
            published.append({"actionId": action.id, "type": "reorder", "moved": moved, "reason": action.reason})
            continue
        if action.type == "add":
            entering = library.get(action.replacement_id or "")
            if action.position is None or entering is None:
                continue
            published.append(
                {
                    "actionId": action.id,
                    "type": "add",
                    "position": action.position,
                    "track": _library_fields(entering),
                    "reason": action.reason,
                }
            )
            continue
        position = positions.get(action.track_id or "")
        if position is None:
            continue
        track = tracks[position - 1]
        item: dict[str, Any] = {
            "actionId": action.id,
            "type": action.type,
            "position": position,
            "title": track["title"],
            "artist": track["artist"],
            "reason": action.reason,
        }
        if action.type == "move":
            if action.to is None:
                continue
            item["to"] = action.to
        elif action.type == "replace_with":
            entering = library.get(action.replacement_id or "")
            if entering is None:
                continue
            item["track"] = _library_fields(entering)
        elif action.type == "replace":
            replacement = library.get(action.replacement_id or "")
            if replacement is None:
                continue
            item["replacement"] = _library_fields(replacement)
        published.append(item)
    return published


def _outside_period(
    backend: HeadlessBackend,
    review: PrepCopilotVariantApplicationResult,
    year_min: int,
    year_max: int,
) -> int:
    """How many tracks of the list a period fit could change right now.

    Only the unprotected tracks whose release year is unknown or outside the range
    count: the protected ones stay whatever the period says.
    """
    protected = backend.review_actions._protected(review)
    return sum(
        1
        for track in review.recommendation.ordered_tracks
        if track.path not in protected and not in_year_range(track, year_min, year_max)
    )


def _library_fields(track: dict[str, Any]) -> dict[str, Any]:
    """The library fields a card shows for a track that would join the list."""
    return {key: track[key] for key in ("title", "artist", "bpm", "key")}


def apply_action(backend: HeadlessBackend, action_id: str) -> dict[str, Any]:
    """Apply one pending change exactly as the equivalent manual review edit.

    Everything that can refuse the change -- an unknown or already applied identity,
    a track that left the list, a track that became protected, a library track that no
    longer exists or an order that no longer describes this list -- is ``stale_ai`` and
    leaves both the review and the pending changes untouched. A ``to`` position and an
    ``add`` slot are applied as written at this click.

    An ``extend`` grows the list through the same ``review.extend`` edit the DJ's own
    button uses and adds its ``extended`` report to the answer; a ``no_candidates``
    refusal is passed through unchanged and the change stays pending. A ``period`` does
    the same through ``review.fit_period`` and adds its ``period`` report. A
    ``use_variant`` is never applied here: choosing an alternative belongs to the
    renderer, so it is ``stale_ai`` and stays pending too.
    """
    store = backend.ai_conversation
    action = store.action(action_id)
    if action is None:
        raise BackendError("stale_ai", _STALE)
    before = backend.review
    extended: dict[str, Any] | None = None
    period: dict[str, Any] | None = None
    try:
        if action.type == "use_variant":
            raise BackendError("stale_ai", _STALE)
        details = backend.review_actions.details()
        review_id = details["reviewId"]
        if action.type == "extend":
            if action.to is None:
                raise BackendError("stale_ai", _STALE)
            grown = backend.review_actions.execute(
                "review.extend", {"reviewId": review_id, "targetTrackCount": action.to}
            )
            extended = grown.pop("extended", None)
            review = grown
        elif action.type == "period":
            if action.year_min is None or action.year_max is None:
                raise BackendError("stale_ai", _STALE)
            fitted = backend.review_actions.execute(
                "review.fit_period",
                {"reviewId": review_id, "yearMin": action.year_min, "yearMax": action.year_max},
            )
            period = fitted.pop("period", None)
            review = fitted
        elif action.type == "undo":
            if not details["canUndo"]:
                raise BackendError("stale_ai", _STALE)
            review = backend.review_actions.execute("review.undo", {"reviewId": review_id})
        elif action.type == "reorder":
            order = list(action.order or ())
            current = [track["id"] for track in details["tracks"]]
            if sorted(order) != sorted(current):
                raise BackendError("stale_ai", _STALE)
            review = backend.review_actions.execute("review.reorder", {"reviewId": review_id, "trackIds": order})
        elif action.type == "add":
            if action.replacement_id is None or action.position is None:
                raise BackendError("stale_ai", _STALE)
            review = backend.review_actions.execute(
                "review.insert",
                {"reviewId": review_id, "trackId": action.replacement_id, "position": action.position},
            )
        else:
            current = [track["id"] for track in details["tracks"]]
            track_id = action.track_id
            if track_id is None or track_id not in current:
                raise BackendError("stale_ai", _STALE)
            if action.type == "move":
                if action.to is None or not 1 <= action.to <= len(current):
                    raise BackendError("stale_ai", _STALE)
                destination = action.to
                order = [item for item in current if item != track_id]
                order.insert(destination - 1, track_id)
                review = backend.review_actions.execute("review.reorder", {"reviewId": review_id, "trackIds": order})
            elif action.type == "remove":
                review = backend.review_actions.execute("review.drop", {"reviewId": review_id, "trackId": track_id})
            elif action.type == "replace_with":
                if action.replacement_id is None:
                    raise BackendError("stale_ai", _STALE)
                review = backend.review_actions.execute(
                    "review.swap",
                    {
                        "reviewId": review_id,
                        "trackId": track_id,
                        "replacementTrackId": action.replacement_id,
                    },
                )
            else:
                comparison = backend.review_actions.execute(
                    "review.compare", {"reviewId": review_id, "trackId": track_id}
                )
                replacement = comparison["replacement"]
                if not comparison["available"] or not isinstance(replacement, dict):
                    raise BackendError("stale_ai", _STALE)
                if replacement["id"] != action.replacement_id:
                    raise BackendError("stale_ai", _STALE)
                review = backend.review_actions.execute(
                    "review.replace",
                    {
                        "reviewId": comparison["reviewId"],
                        "trackId": track_id,
                        "replacementId": replacement["id"],
                    },
                )
    except BackendError as error:
        if error.code in ("stale_ai", "no_candidates"):
            raise
        raise BackendError("stale_ai", _STALE) from None
    answer: dict[str, Any] = {"review": review, "actions": public_actions(backend, store.applied(action.id))}
    # S7: the conversation remembers what its own applied proposal did to the list, so the
    # next answer reads it as already applied instead of proposing it again. The lines are
    # the ones every applied edit already reads: positions, titles and artists, no path.
    if before is not None and backend.review is not None:
        store.note_confirmed(
            applied_changes(before.recommendation.ordered_tracks, backend.review.recommendation.ordered_tracks)
        )
    if extended is not None:
        answer["extended"] = extended
    if period is not None:
        answer["period"] = period
    return answer


def _offered_variant(backend: HeadlessBackend, current: str, named: Any) -> tuple[int | None, str]:
    """The length of the alternative a ``use_variant`` names, or why it cannot be bound.

    The alternative already in use is not an alternative to offer, and a name the plan
    does not carry cannot be applied at all.
    """
    plan = backend.plan
    if plan is None or not isinstance(named, str):
        return None, _NO_VARIANT
    for variant in plan.variants:
        if variant.name != named:
            continue
        if named == current:
            return None, _SAME_VARIANT
        return len(variant.recommendation.ordered_tracks), ""
    return None, _NO_VARIANT


def _offered_replacement(backend: HeadlessBackend, review_id: str, track_id: str) -> dict[str, Any] | None:
    """Ask the comparison edit, locally, which replacement it would apply right now."""
    try:
        comparison = backend.review_actions.execute("review.compare", {"reviewId": review_id, "trackId": track_id})
    except BackendError:
        return None
    replacement = comparison["replacement"]
    return replacement if comparison["available"] and isinstance(replacement, dict) else None


__all__ = ["apply_action", "propose_actions", "public_actions"]
