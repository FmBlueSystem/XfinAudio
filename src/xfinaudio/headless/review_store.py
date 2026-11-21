"""App-owned recovery file for the generated review in progress (S6).

One file under the data directory, written atomically after every change. It is
the only durable copy of a review that lives in memory, so reading is strict:
a missing, corrupt or out-of-contract file is ignored with a logged warning and
never stops the core. Paths never leave this module and never reach the renderer.
"""

from __future__ import annotations

import contextlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from xfinaudio.headless.saved_review import SAVED_VARIANT

LOGGER = logging.getLogger(__name__)
STORE_NAME = "active_review.json"
VERSION = 2
MAX_STORE_BYTES = 4 * 1024 * 1024
VARIANT_NAMES = ("safe", "balanced", "adventurous", SAVED_VARIANT)
READINESS_STATUSES = ("ready", "needs_review", "blocked")
FIELDS = ("version", "reviewId", "planId", "name", "variant", "warnings", "variants", "review", "plan", "removed")
# Only a saved list carries the playlist it stays tied to (S3); a generated review never does.
SAVED_FIELD = "savedPlaylist"
SAVED_FIELDS = (*FIELDS, SAVED_FIELD)
SAVED_PLAYLIST_FIELDS = {"id", "name", "createdAt", "updatedAt", "trackPaths"}
VARIANT_FIELDS = {
    "name",
    "description",
    "trackCount",
    "readiness",
    "warnings",
    "blockers",
    "qualityScore",
}


def store_path(data_dir: Path) -> Path:
    """Return the single app-owned file that holds the review in progress."""
    return data_dir / STORE_NAME


def _valid_identity(value: Any) -> bool:
    try:
        return isinstance(value, str) and str(UUID(value)) == value
    except ValueError:
        return False


def _texts(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _variant(value: Any) -> bool:
    """Accept only the public variant summary the renderer already knows how to read."""
    return (
        isinstance(value, dict)
        and set(value) == VARIANT_FIELDS
        and value["name"] in VARIANT_NAMES
        and isinstance(value["description"], str)
        and type(value["trackCount"]) is int
        and value["trackCount"] >= 0
        and value["readiness"] in READINESS_STATUSES
        and _texts(value["warnings"])
        and _texts(value["blockers"])
        and type(value["qualityScore"]) in (int, float)
    )


def _timestamp(value: Any) -> bool:
    """Accept only a time the core can read back as the moment it stored."""
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value)
    except ValueError:
        return False
    return True


def _saved_playlist(value: Any) -> bool:
    """Accept only the playlist snapshot a restored saved list stays tied to (S3)."""
    return (
        isinstance(value, dict)
        and set(value) == SAVED_PLAYLIST_FIELDS
        and type(value["id"]) is int
        and value["id"] > 0
        and isinstance(value["name"], str)
        and bool(value["name"].strip())
        and _timestamp(value["createdAt"])
        and _timestamp(value["updatedAt"])
        and _texts(value["trackPaths"])
    )


def _valid(payload: Any) -> bool:
    """Accept exactly the recovery contract this version writes, or the one written before it.

    Version 1 is the file a build that could not recover a saved list wrote: a generated
    review and nothing else. Version 2 adds the saved playlist a saved list is tied to,
    and only a saved list carries it, so a stored saved list and a stored generation can
    never be mistaken for each other.
    """
    if not isinstance(payload, dict) or set(payload) not in (set(FIELDS), set(SAVED_FIELDS)):
        return False
    linked = SAVED_FIELD in payload
    return (
        type(payload["version"]) is int
        and payload["version"] in ((VERSION,) if linked else (1, VERSION))
        and _valid_identity(payload["reviewId"])
        and _valid_identity(payload["planId"])
        and isinstance(payload["name"], str)
        and bool(payload["name"].strip())
        and payload["variant"] in VARIANT_NAMES
        and (payload["variant"] == SAVED_VARIANT) == linked
        and _texts(payload["warnings"])
        and isinstance(payload["variants"], list)
        and all(_variant(item) for item in payload["variants"])
        and isinstance(payload["review"], dict)
        and isinstance(payload["plan"], dict)
        and _texts(payload["removed"])
        and (not linked or _saved_playlist(payload[SAVED_FIELD]))
    )


def read_review(data_dir: Path) -> dict[str, Any] | None:
    """Return the stored review only when it matches the contract; otherwise warn and ignore it."""
    path = store_path(data_dir)
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        return None
    except OSError:
        LOGGER.warning("The list in progress could not be read; it is dropped")
        return None
    if size > MAX_STORE_BYTES:
        LOGGER.warning("The stored list in progress is larger than the contract allows; it is dropped")
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError, RecursionError):
        LOGGER.warning("The stored list in progress is not valid JSON; it is dropped")
        return None
    if not _valid(payload):
        LOGGER.warning("The stored list in progress does not match the recovery contract; it is dropped")
        return None
    return payload


def write_review(data_dir: Path, payload: dict[str, Any]) -> None:
    """Atomically replace the file, so a failed write never leaves a half-record."""
    if not _valid(payload):
        raise ValueError("The review in progress does not match the recovery contract")
    pending = data_dir / f"{STORE_NAME}.tmp"
    try:
        pending.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        pending.replace(store_path(data_dir))
    except OSError:
        with contextlib.suppress(OSError):
            pending.unlink(missing_ok=True)
        raise


def clear_review(data_dir: Path) -> None:
    """Forget a discarded review; a refused removal is reported and never fatal."""
    try:
        store_path(data_dir).unlink(missing_ok=True)
    except OSError:
        LOGGER.warning("The stored list in progress could not be removed")
