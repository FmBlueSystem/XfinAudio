"""Opt-in diagnostic log of the list-assistant conversation.

The list assistant promises that the conversation itself never reaches the disk, and
that promise holds unless the DJ starts the core with ``XFINAUDIO_CHAT_LOG=1``. With
that variable the core appends one JSON line per assistant event to
``logs/list-chat.log`` inside the data directory, so a support session can read what the
DJ asked, what the provider answered and which proposed changes were refused.

The writer is deliberately dumb and total: the file is created ``0600``, a file that
passes two megabytes is rotated to ``list-chat.log.1`` (replacing the previous one), and
any failure to write is ignored. A diagnostic log is never allowed to fail the turn or
the apply it describes.

What never reaches a line is decided by the caller: the shapes written here carry the
DJ's own words, the provider text, titles and positions, and no file path, no track
identity, no credential and no system message.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

#: The only switch: with any other value (or no variable at all) nothing is written.
CHAT_LOG_ENV = "XFINAUDIO_CHAT_LOG"
CHAT_LOG_DIRECTORY = "logs"
CHAT_LOG_NAME = "list-chat.log"
CHAT_LOG_BACKUP_NAME = "list-chat.log.1"
#: The log is renamed once one more line would pass this size.
MAX_CHAT_LOG_BYTES = 2 * 1024 * 1024
#: The conversation is private: the file is readable by its owner only.
FILE_MODE = 0o600


def chat_log_enabled(environment: Mapping[str, str] | None = None) -> bool:
    """Whether the DJ opted in for this process."""
    env = os.environ if environment is None else environment
    return env.get(CHAT_LOG_ENV) == "1"


class ChatLog:
    """Append one JSON line per list-assistant event, or nothing at all."""

    def __init__(self, data_dir: Path | str) -> None:
        self.path = Path(data_dir) / CHAT_LOG_DIRECTORY / CHAT_LOG_NAME
        self.backup_path = self.path.with_name(CHAT_LOG_BACKUP_NAME)

    def write(self, event: str, **fields: Any) -> None:
        """Append ``fields`` with ``time`` and ``event``; never raise and never fail a turn."""
        if not chat_log_enabled():
            return
        line = self._line(event, fields)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._rotate_if_needed(len(line))
            descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, FILE_MODE)
            try:
                os.fchmod(descriptor, FILE_MODE)
                os.write(descriptor, line)
            finally:
                os.close(descriptor)
        except OSError:
            # A read-only directory or a file sitting where the log belongs is silent:
            # the turn it describes keeps working exactly as it did before.
            return

    @staticmethod
    def _line(event: str, fields: Mapping[str, Any]) -> bytes:
        record = {"time": datetime.now(UTC).isoformat(), "event": event, **fields}
        return (json.dumps(record, ensure_ascii=False, default=str) + "\n").encode("utf-8")

    def _rotate_if_needed(self, incoming: int) -> None:
        """Rename the log to its single backup once one more line would pass the cap."""
        try:
            size = self.path.stat().st_size
        except OSError:
            return
        if size + incoming <= MAX_CHAT_LOG_BYTES:
            return
        self.path.replace(self.backup_path)


__all__ = [
    "CHAT_LOG_BACKUP_NAME",
    "CHAT_LOG_DIRECTORY",
    "CHAT_LOG_ENV",
    "CHAT_LOG_NAME",
    "FILE_MODE",
    "MAX_CHAT_LOG_BYTES",
    "ChatLog",
    "chat_log_enabled",
]
