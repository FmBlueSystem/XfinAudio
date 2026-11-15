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


def propose_actions(
    backend: HeadlessBackend, review_id: str, items: Sequence[Mapping[str, Any]]
) -> tuple[tuple[ChatAction, ...], int]:
    """Bind this turn's validated proposals to the tracks they named.

    ``items`` is the parsed answer's own shape (``type``, ``position``, ``reason``
    and, for a move, ``to``). A proposal whose track is no longer in the list, or
    whose ``replace`` has no replacement the engine still offers, is dropped and
    counted instead of failing the turn.
    """
    review = backend.review
    if review is None:
        return (), len(items)
    tracks = list(review.recommendation.ordered_tracks)
    accepted: list[ChatAction] = []
    dropped = 0
    for item in items:
        position, reason = item["position"], item["reason"]
        if not 1 <= position <= len(tracks):
            dropped += 1
            continue
        track_id = _public_track(tracks[position - 1])["id"]
        if item["type"] == "move":
            accepted.append(ChatAction(str(uuid4()), "move", track_id, item["to"], reason))
            continue
        replacement = _offered_replacement(backend, review_id, track_id)
        if replacement is None:
            dropped += 1
            continue
        accepted.append(ChatAction(str(uuid4()), "replace", track_id, None, reason, replacement["id"]))
    return tuple(accepted), dropped


def public_actions(backend: HeadlessBackend, actions: Iterable[ChatAction]) -> list[dict[str, Any]]:
    """The pending changes as the DJ sees them, at their current positions.

    A change whose track left the list, or whose replacement is no longer in the
    library, is not offered: it cannot be applied any more.
    """
    review = backend.review
    if review is None:
        return []
    tracks = [_public_track(track) for track in review.recommendation.ordered_tracks]
    positions = {track["id"]: index for index, track in enumerate(tracks, start=1)}
    library = {_public_track(record)["id"]: _public_track(record) for record in backend._records()}
    published: list[dict[str, Any]] = []
    for action in actions:
        position = positions.get(action.track_id)
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
    """
    store = backend.ai_conversation
    action = store.action(action_id)
    if action is None:
        raise BackendError("stale_ai", _STALE)
    try:
        details = backend.review_actions.details()
        current = [track["id"] for track in details["tracks"]]
        if action.track_id not in current:
            raise BackendError("stale_ai", _STALE)
        if action.type == "move":
            if action.to is None or not 1 <= action.to <= len(current):
                raise BackendError("stale_ai", _STALE)
            order = [track_id for track_id in current if track_id != action.track_id]
            order.insert(action.to - 1, action.track_id)
            review = backend.review_actions.execute(
                "review.reorder", {"reviewId": details["reviewId"], "trackIds": order}
            )
        else:
            comparison = backend.review_actions.execute(
                "review.compare", {"reviewId": details["reviewId"], "trackId": action.track_id}
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
                    "trackId": action.track_id,
                    "replacementId": replacement["id"],
                },
            )
    except BackendError as error:
        if error.code == "stale_ai":
            raise
        raise BackendError("stale_ai", _STALE) from None
    return {"review": review, "actions": public_actions(backend, store.applied(action.id))}


def _offered_replacement(backend: HeadlessBackend, review_id: str, track_id: str) -> dict[str, Any] | None:
    """Ask the comparison edit, locally, which replacement it would apply right now."""
    try:
        comparison = backend.review_actions.execute("review.compare", {"reviewId": review_id, "trackId": track_id})
    except BackendError:
        return None
    replacement = comparison["replacement"]
    return replacement if comparison["available"] and isinstance(replacement, dict) else None


__all__ = ["apply_action", "propose_actions", "public_actions"]
