"""One in-memory conversation about the generated list, never written to disk.

The conversation belongs to the list in progress, not to a review revision: an
edit of the list (undo, remove, reorder, replace) keeps it, so a later turn can
talk about the change. It ends with the process, with an explicit reset, or when
the core discards the generated review.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

#: Messages kept across turns; the oldest pair is dropped once the list is longer.
MESSAGE_LIMIT = 40
#: Messages sent with the new question; the rest stay readable but are not resent.
PROMPT_LIMIT = 20


@dataclass(frozen=True)
class Message:
    """One stored turn: a user question or an assistant reply."""

    role: str
    text: str

    def public(self) -> dict[str, str]:
        return {"role": self.role, "text": self.text}


@dataclass(frozen=True)
class ChatAction:
    """One validated change the assistant proposed, bound to the track it named.

    ``type`` is ``replace`` (take that track out and put the engine's replacement in
    its place) or ``move``. ``track_id`` and ``replacement_id`` are internal public
    track identities and are never published: the answer carries titles, positions
    and reasons only.
    """

    id: str
    type: str
    track_id: str
    to: int | None
    reason: str
    replacement_id: str | None = None


class ConversationStore:
    """The single conversation about the list in progress, kept in memory only."""

    def __init__(self) -> None:
        self._messages: list[Message] = []
        self._list: str | None = None
        self._actions: tuple[ChatAction, ...] = ()

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

    def record(self, fingerprint: str, request: str, reply: str) -> list[dict[str, str]]:
        """Store one successful turn and return the whole conversation, oldest first."""
        self._messages.extend((Message("user", request), Message("assistant", reply)))
        # Turns are stored two messages at a time, so the oldest pair is what falls out.
        while len(self._messages) > MESSAGE_LIMIT:
            del self._messages[:2]
        self._list = fingerprint
        return self.snapshot()

    def reset(self) -> list[dict[str, str]]:
        """Forget the conversation, the changes it proposed and the list it read."""
        self._messages.clear()
        self._list = None
        self._actions = ()
        return []


__all__ = ["MESSAGE_LIMIT", "PROMPT_LIMIT", "ChatAction", "ConversationStore", "Message"]
