"""One in-memory conversation about the generated list, never written to disk.

The conversation belongs to the list in progress, not to a review revision: an
edit of the list (undo, remove, reorder, replace) keeps it, so a later turn can
talk about the change. It ends with the process, with an explicit reset, or when
the core discards the generated review.
"""

from __future__ import annotations

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


class ConversationStore:
    """The single conversation about the list in progress, kept in memory only."""

    def __init__(self) -> None:
        self._messages: list[Message] = []
        self._list: str | None = None

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
        """Forget the conversation and the list it read."""
        self._messages.clear()
        self._list = None
        return []


__all__ = ["MESSAGE_LIMIT", "PROMPT_LIMIT", "ConversationStore", "Message"]
