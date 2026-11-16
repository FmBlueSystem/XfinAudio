"""One in-memory conversation about the generated list, never written to disk.

The conversation belongs to the list in progress, not to a review revision: an
edit of the list (undo, remove, reorder, replace) keeps it, so a later turn can
talk about the change. It ends with the process, with an explicit reset, or when
the core discards the generated review.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from xfinaudio.library.models import TrackRecord

#: Messages kept across turns; the oldest pair is dropped once the list is longer.
MESSAGE_LIMIT = 40
#: Messages sent with the new question; the rest stay readable but are not resent.
PROMPT_LIMIT = 20
#: The most applied changes one turn reports; the oldest fall out first.
APPLIED_LIMIT = 20
#: The longest title or artist one change line names.
_MAX_NAMED_CHARS = 80
#: The most lines one applied edit describes; a wholesale change is summarized instead.
_MAX_LINES_PER_EDIT = 4


@dataclass(frozen=True)
class Message:
    """One stored turn: a user question or an assistant reply."""

    role: str
    text: str

    def public(self) -> dict[str, str]:
        return {"role": self.role, "text": self.text}


@dataclass(frozen=True)
class ChatAction:
    """One validated change the assistant proposed, bound to what it named.

    ``type`` is ``replace`` (take that track out and put the engine's replacement in
    its place), ``remove`` (take it out without a replacement), ``move``, ``reorder``
    (the ``order`` of the tracks as it was proposed) or ``undo``; ``add`` puts the
    library track in ``replacement_id`` at the slot ``position``, ``replace_with``
    swaps the listed track for that library one, ``extend`` grows the list to ``to``
    tracks and ``use_variant`` switches to the plan alternative ``variant``, whose
    length was ``track_count`` when it was proposed. ``track_id``, ``replacement_id``
    and ``order`` are internal public track identities and are never published: the
    answer carries titles, positions and reasons only. A list-level change names no
    track, so its ``track_id`` stays empty.
    """

    id: str
    type: str
    track_id: str | None
    to: int | None
    reason: str
    replacement_id: str | None = None
    variant: str | None = None
    track_count: int | None = None
    position: int | None = None
    order: tuple[str, ...] | None = None


def applied_changes(previous: Sequence[TrackRecord], current: Sequence[TrackRecord]) -> tuple[str, ...]:
    """The short Spanish lines one applied edit reads, oldest change first.

    The lines are computed from the two lists themselves, so a change the DJ made by
    hand, one the assistant's card applied and an undo or redo all describe the same
    way: what the list had, what it has now, and where. A line names positions, titles
    and artists only, so nothing here can carry a file path or a track identity.
    """
    before, after = list(previous), list(current)
    if [track.path for track in before] == [track.path for track in after]:
        return ()
    stayed = {track.path for track in after}
    was = {track.path for track in before}
    removed = [(position, track) for position, track in enumerate(before, start=1) if track.path not in stayed]
    added = [(position, track) for position, track in enumerate(after, start=1) if track.path not in was]
    if not removed and not added:
        return (_order_line(before, after),)
    if not removed and len(added) > 1 and all(position > len(before) for position, _ in added):
        return (f"Ampliar la lista a {len(after)} pistas",)
    lines: list[str] = []
    paired: set[int] = set()
    for position, track in removed:
        replaced = next((item for item in added if item[0] == position), None)
        if replaced is None:
            lines.append(f"Quitar la posición {position}: {_named(track)}")
            continue
        paired.add(replaced[0])
        lines.append(f"Reemplazar la posición {position}: {_named(track)} por {_named(replaced[1])}")
    lines.extend(
        f"Agregar en la posición {position}: {_named(track)}" for position, track in added if position not in paired
    )
    return _bounded(lines)


def _order_line(before: Sequence[TrackRecord], after: Sequence[TrackRecord]) -> str:
    """The one line a change that only moved tracks around reads."""
    move = _single_move(before, after)
    if move is not None:
        track, origin, destination = move
        return f"Mover la posición {origin} a la posición {destination}: {_named(track)}"
    moved = sum(1 for index, track in enumerate(before) if after[index].path != track.path)
    return f"Reordenar la lista: {moved} pistas cambian de lugar"


def _single_move(before: Sequence[TrackRecord], after: Sequence[TrackRecord]) -> tuple[TrackRecord, int, int] | None:
    """The one track a pure move took out and put back elsewhere, or nothing."""
    paths = [track.path for track in after]
    for origin, track in enumerate(before, start=1):
        rest = [item.path for index, item in enumerate(before, start=1) if index != origin]
        if sorted(rest) != sorted(paths):
            continue
        for destination in range(1, len(before) + 1):
            if rest[: destination - 1] + [track.path] + rest[destination - 1 :] == paths:
                return track, origin, destination
    return None


def _named(track: TrackRecord) -> str:
    """One track as a change line names it: its title and its artist, never its path."""
    title = (track.title or "(sin título)")[:_MAX_NAMED_CHARS]
    artist = (track.artist or "(artista desconocido)")[:_MAX_NAMED_CHARS]
    return f"«{title}» — {artist}"


def _bounded(lines: list[str]) -> tuple[str, ...]:
    """The lines of one edit, summarized when the edit replaced almost the whole list."""
    if len(lines) <= _MAX_LINES_PER_EDIT:
        return tuple(lines)
    return (*lines[:_MAX_LINES_PER_EDIT], f"y {len(lines) - _MAX_LINES_PER_EDIT} cambios más")


class ConversationStore:
    """The single conversation about the list in progress, kept in memory only."""

    def __init__(self) -> None:
        self._messages: list[Message] = []
        self._list: str | None = None
        self._actions: tuple[ChatAction, ...] = ()
        # The library tracks a search showed, each with the short reference the assistant
        # may name later: ``L1``, ``L2``... and nothing else, valid for this conversation.
        self._references: dict[str, str] = {}
        self._named: dict[str, str] = {}
        # The tracks this conversation already showed, most recently found first, so a
        # later turn can offer them again without repeating a search.
        self._recent: list[str] = []
        # What the DJ changed in the list since the previous successful turn, oldest
        # first, as short lines that name positions and titles and never an identity.
        self._applied: list[str] = []

    @property
    def first_turn(self) -> bool:
        """True while no successful turn has been stored, so consent is still due."""
        return not self._messages

    def snapshot(self) -> list[dict[str, str]]:
        """The whole stored conversation, oldest first."""
        return [message.public() for message in self._messages]

    def prompt(self) -> list[dict[str, str]]:
        """At most the last ``PROMPT_LIMIT`` messages, oldest first."""
        return [message.public() for message in self._messages[-PROMPT_LIMIT:]]

    def actions(self) -> tuple[ChatAction, ...]:
        """The changes still pending, in the order they were proposed."""
        return self._actions

    def action(self, action_id: str) -> ChatAction | None:
        """The pending change with this identity, if it is still pending."""
        return next((action for action in self._actions if action.id == action_id), None)

    def record_actions(self, actions: Iterable[ChatAction]) -> tuple[ChatAction, ...]:
        """Replace the pending changes with one successful turn's proposals."""
        self._actions = tuple(actions)
        return self._actions

    def applied(self, action_id: str) -> tuple[ChatAction, ...]:
        """Forget one applied change and return the ones still pending."""
        self._actions = tuple(action for action in self._actions if action.id != action_id)
        return self._actions

    def list_changed(self, fingerprint: str) -> bool:
        """True when this turn reads a different list than the last successful turn."""
        return self._list is not None and self._list != fingerprint

    def reference(self, track_id: str) -> str:
        """The conversation-scoped short reference for one library track.

        A track already shown keeps its reference, so a reference the assistant read
        in an earlier turn still names the same track; every new one gets the next
        number in order, and the track becomes the most recently found one.
        """
        existing = self._references.get(track_id)
        if existing is not None:
            self._recent = [track_id, *(item for item in self._recent if item != track_id)]
            return existing
        reference = f"L{len(self._references) + 1}"
        self._references[track_id] = reference
        self._named[reference] = track_id
        self._recent = [track_id, *self._recent]
        return reference

    def referenced(self, reference: str) -> str | None:
        """The library track this conversation gave that reference to, if it ever did."""
        return self._named.get(reference)

    def references(self) -> tuple[tuple[str, str], ...]:
        """The references this conversation issued, most recent first, with their track."""
        return tuple((self._references[track_id], track_id) for track_id in self._recent)

    def note_applied(self, lines: Iterable[str]) -> tuple[str, ...]:
        """Record the changes applied to the list since the previous successful turn.

        A change made before the conversation's first successful turn belongs to the
        state the DJ handed over, not to a previous answer, so nothing is recorded yet.
        """
        if self._messages:
            self._applied.extend(lines)
            del self._applied[:-APPLIED_LIMIT]
        return self.applied_since_turn()

    def applied_since_turn(self) -> tuple[str, ...]:
        """The changes applied since the previous successful turn, oldest first."""
        return tuple(self._applied)

    def record(self, fingerprint: str, request: str, reply: str) -> list[dict[str, str]]:
        """Store one successful turn and return the whole conversation, oldest first."""
        self._messages.extend((Message("user", request), Message("assistant", reply)))
        # Turns are stored two messages at a time, so the oldest pair is what falls out.
        while len(self._messages) > MESSAGE_LIMIT:
            del self._messages[:2]
        self._list = fingerprint
        # The changes were reported in this turn's system message, so the next turn
        # reports only what the DJ applies from now on.
        self._applied.clear()
        return self.snapshot()

    def reset(self) -> list[dict[str, str]]:
        """Forget the conversation, the changes it proposed and the references it issued."""
        self._messages.clear()
        self._list = None
        self._actions = ()
        self._references.clear()
        self._named.clear()
        self._recent.clear()
        self._applied.clear()
        return []


__all__ = [
    "APPLIED_LIMIT",
    "MESSAGE_LIMIT",
    "PROMPT_LIMIT",
    "ChatAction",
    "ConversationStore",
    "Message",
    "applied_changes",
]
