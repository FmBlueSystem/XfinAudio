"""The assistant's proposed list changes: kept in memory, published without identities, applied as edits.

The assistant never changes the list by itself. One successful chat turn may propose
up to five changes; the core binds each one to the track it named (never to its
position), computes the replacement a ``replace`` would use and keeps the result next
to the conversation, in memory only. The DJ applies one on request, and that apply
goes through exactly the code a manual review edit uses: a new revision, undoable and
stored like any other edit. Applying never contacts the provider.

Nothing published here carries a file path or a track identity: the answer names a
position, the title and artist of the track, and, for a replacement, its fields.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from xfinaudio.headless.ai_conversation import ChatAction
from xfinaudio.headless.common import BackendError, _public_track

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from xfinaudio.headless.backend import HeadlessBackend

_STALE = "Apply a change that is still pending and still possible"
#: Why a proposal could not be bound to the list; the opt-in chat log repeats it verbatim.
_NO_LIST = "no current list"
_TRACK_LEFT = "track left the list"
_NO_REPLACEMENT = "no replacement offered"
_SAME_VARIANT = "the list already uses that alternative"
_NO_VARIANT = "no such alternative in the plan"


def propose_actions(
    backend: HeadlessBackend, review_id: str, items: Sequence[Mapping[str, Any]]
) -> tuple[tuple[ChatAction, ...], tuple[tuple[Mapping[str, Any], str], ...]]:
    """Bind this turn's validated proposals to what they named.

    ``items`` is the parsed answer's own shape (``type``, ``reason`` and, depending on
    the type, ``position``, ``to`` or ``variant``). A proposal whose track is no
    longer in the list, whose ``replace`` has no replacement the engine still offers
    or whose ``use_variant`` names the alternative already in use is dropped and
    counted instead of failing the turn; it is returned with the reason it was
    dropped for the opt-in chat log.
    """
    review = backend.review
    if review is None:
        return (), tuple((item, _NO_LIST) for item in items)
    tracks = list(review.recommendation.ordered_tracks)
    accepted: list[ChatAction] = []
    dropped: list[tuple[Mapping[str, Any], str]] = []
    for item in items:
        kind, reason = item["type"], item["reason"]
        if kind == "extend":
            accepted.append(ChatAction(str(uuid4()), "extend", None, item["to"], reason))
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
        position = item["position"]
        if not 1 <= position <= len(tracks):
            dropped.append((item, _TRACK_LEFT))
            continue
        track_id = _public_track(tracks[position - 1])["id"]
        if kind == "move":
            accepted.append(ChatAction(str(uuid4()), "move", track_id, item["to"], reason))
            continue
        replacement = _offered_replacement(backend, review_id, track_id)
        if replacement is None:
            dropped.append((item, _NO_REPLACEMENT))
            continue
        accepted.append(ChatAction(str(uuid4()), "replace", track_id, None, reason, replacement["id"]))
    return tuple(accepted), tuple(dropped)


def public_actions(backend: HeadlessBackend, actions: Iterable[ChatAction]) -> list[dict[str, Any]]:
    """The pending changes as the DJ sees them, at their current positions.

    A change whose track left the list, or whose replacement is no longer in the
    library, is not offered: it cannot be applied any more. Only the stored library
    records are consulted here, so publishing never re-reads the library from disk.
    """
    review = backend.review
    if review is None:
        return []
    tracks = [_public_track(track) for track in review.recommendation.ordered_tracks]
    positions = {track["id"]: index for index, track in enumerate(tracks, start=1)}
    library = {_public_track(record)["id"]: _public_track(record) for record in backend._records(checked=frozenset())}
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
        else:
            replacement = library.get(action.replacement_id or "")
            if replacement is None:
                continue
            item["replacement"] = {key: replacement[key] for key in ("title", "artist", "bpm", "key")}
        published.append(item)
    return published


def apply_action(backend: HeadlessBackend, action_id: str) -> dict[str, Any]:
    """Apply one pending change exactly as the equivalent manual review edit.

    Everything that can refuse the change -- an unknown or already applied identity,
    a track that left the list, a track that became protected, a replacement the
    engine no longer offers -- is ``stale_ai`` and leaves both the review and the
    pending changes untouched. A ``to`` position is applied as written at this click.

    An ``extend`` grows the list through the same ``review.extend`` edit the DJ's own
    button uses and adds its ``extended`` report to the answer; a ``no_candidates``
    refusal is passed through unchanged and the change stays pending. A
    ``use_variant`` is never applied here: choosing an alternative belongs to the
    renderer, so it is ``stale_ai`` and stays pending too.
    """
    store = backend.ai_conversation
    action = store.action(action_id)
    if action is None:
        raise BackendError("stale_ai", _STALE)
    extended: dict[str, Any] | None = None
    try:
        if action.type == "use_variant":
            raise BackendError("stale_ai", _STALE)
        details = backend.review_actions.details()
        if action.type == "extend":
            if action.to is None:
                raise BackendError("stale_ai", _STALE)
            grown = backend.review_actions.execute(
                "review.extend", {"reviewId": details["reviewId"], "targetTrackCount": action.to}
            )
            extended = grown.pop("extended", None)
            review = grown
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
                review = backend.review_actions.execute(
                    "review.reorder", {"reviewId": details["reviewId"], "trackIds": order}
                )
            else:
                comparison = backend.review_actions.execute(
                    "review.compare", {"reviewId": details["reviewId"], "trackId": track_id}
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
    if extended is not None:
        answer["extended"] = extended
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
