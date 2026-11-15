"""Explicit persistent Prep controls using original app-owned BuildSessionSettings."""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from xfinaudio.config.settings import BuildSessionSettings, PrepFormSettings
from xfinaudio.config.settings_repository import SettingsRepositoryError
from xfinaudio.headless.common import BackendError, _inside, _public_track

if TYPE_CHECKING:
    from xfinaudio.headless.backend import HeadlessBackend
    from xfinaudio.recommendation.prep_copilot import DJSetIntent

LOGGER = logging.getLogger(__name__)

PREP_SETTINGS_FIELDS = {
    "prep.settings.get": set(),
    "prep.settings.update": {"revision", "requiredTrackIds", "excludedTrackIds", "genreFocus", "clearUnavailable"},
}

# The last accepted form is its own app-owned file: remembering it must never
# rewrite settings.json or move the preferences revision an editor already holds.
FORM_STORE_NAME = "prep_form.json"
FORM_STORE_VERSION = 1
FORM_STORE_FIELDS = ("version", "form")
MAX_FORM_STORE_BYTES = 64 * 1024


def form_store_path(data_dir: Path) -> Path:
    """Return the single app-owned file that holds the last accepted Prep form."""
    return data_dir / FORM_STORE_NAME


def read_form(data_dir: Path) -> PrepFormSettings | None:
    """Return the remembered form only when it matches the contract; otherwise warn and ignore it."""
    path = form_store_path(data_dir)
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        return None
    except OSError:
        LOGGER.warning("The remembered Prep form could not be read; it is dropped")
        return None
    if size > MAX_FORM_STORE_BYTES:
        LOGGER.warning("The remembered Prep form is larger than the contract allows; it is dropped")
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError, RecursionError):
        LOGGER.warning("The remembered Prep form is not valid JSON; it is dropped")
        return None
    if not isinstance(payload, dict) or set(payload) != set(FORM_STORE_FIELDS):
        LOGGER.warning("The remembered Prep form does not match the store contract; it is dropped")
        return None
    if type(payload["version"]) is not int or payload["version"] != FORM_STORE_VERSION:
        LOGGER.warning("The remembered Prep form does not match the store contract; it is dropped")
        return None
    try:
        return PrepFormSettings.model_validate(payload["form"])
    except ValidationError:
        LOGGER.warning("The remembered Prep form does not match the Prep contract; it is dropped")
        return None


def write_form(data_dir: Path, form: PrepFormSettings) -> None:
    """Atomically replace the file, so a failed write never leaves a half-record."""
    payload = {"version": FORM_STORE_VERSION, "form": form.model_dump(mode="json")}
    pending = data_dir / f"{FORM_STORE_NAME}.tmp"
    try:
        pending.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        pending.replace(form_store_path(data_dir))
    except OSError:
        with contextlib.suppress(OSError):
            pending.unlink(missing_ok=True)
        raise


def _identity(path: str) -> str:
    """The opaque public identity of a path, also after the track left the library."""
    return hashlib.sha256(path.encode("utf-8")).hexdigest()


class PrepSettings:
    def __init__(self, backend: HeadlessBackend) -> None:
        self.backend = backend

    def _paths(self) -> dict[str, str]:
        return {
            _public_track(track)["id"]: track.path
            for track in self.backend._records()
            if Path(track.path).is_file() and any(_inside(Path(track.path), root) for root in self.backend.roots)
        }

    def execute(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if set(params) != PREP_SETTINGS_FIELDS[method]:
            raise BackendError("invalid_params", "Missing or unexpected Prep preference fields")
        preferences = self.backend.preferences
        try:
            with preferences._lock():
                preferences._load()
                assert preferences.settings is not None
                paths = self._paths()
                build = preferences.settings.build
                if method == "prep.settings.update":
                    if (
                        not isinstance(params["revision"], str)
                        or re.fullmatch(r"[0-9a-f]{64}", params["revision"]) is None
                    ):
                        raise BackendError("invalid_params", "Invalid preference revision")
                    if params["revision"] != preferences.revision:
                        raise BackendError("stale_settings", "Prep preferences changed; refresh before saving")
                    genre, clear = params["genreFocus"], params["clearUnavailable"]
                    if not isinstance(genre, str) or len(genre) > 100 or "\x00" in genre or type(clear) is not bool:
                        raise BackendError("invalid_params", "Invalid Prep preference value")
                    selections = []
                    for field, previous in (
                        ("requiredTrackIds", build.locked_paths),
                        ("excludedTrackIds", build.excluded_paths),
                    ):
                        values = params[field]
                        if (
                            not isinstance(values, list)
                            or len(values) > 100
                            or any(not isinstance(value, str) or value not in paths for value in values)
                            or len(set(values)) != len(values)
                        ):
                            raise BackendError(
                                "invalid_params", "Choose at most 100 distinct available authorized tracks"
                            )
                        retained = set() if clear else set(previous) - set(paths.values())
                        selections.append(frozenset(paths[value] for value in values) | retained)
                    required, excluded = selections
                    if required & excluded:
                        raise BackendError("invalid_params", "A required track cannot also be excluded")
                    build = BuildSessionSettings(
                        locked_paths=required, excluded_paths=excluded, genre_focus=genre.strip() or None
                    )
                    preferences._save(preferences.settings.model_copy(update={"build": build}))
                    self.backend.invalidate_review()
                    self.backend.live.invalidate()
                    self.backend.invalidate_optional_ai()
                ids = {path: identity for identity, path in paths.items()}
                remembered = read_form(self.backend.data_dir) or PrepFormSettings()
                return {
                    "revision": preferences.revision,
                    "requiredTrackIds": sorted(ids[path] for path in build.locked_paths if path in ids),
                    "excludedTrackIds": sorted(ids[path] for path in build.excluded_paths if path in ids),
                    "genreFocus": build.genre_focus or "",
                    "unavailableRequiredCount": len(build.locked_paths - ids.keys()),
                    "unavailableExcludedCount": len(build.excluded_paths - ids.keys()),
                    "lastForm": self._remembered_form(remembered, ids),
                }
        except (OSError, SettingsRepositoryError) as error:
            raise BackendError(
                "settings_unavailable", "App-owned Prep preferences are unavailable; no settings were applied"
            ) from error

    @staticmethod
    def _remembered_form(form: PrepFormSettings, ids: dict[str, str]) -> dict[str, Any]:
        """Project the stored form to the public shape, keeping missing tracks identifiable."""

        def remembered(path: str | None) -> str | None:
            if path is None:
                return None
            return ids.get(path) or _identity(path)

        return {
            "targetTrackCount": form.target_track_count,
            "targetMinutes": form.target_minutes,
            "strategy": form.strategy,
            "slotRole": form.slot_role,
            "name": form.name,
            "startTrackId": remembered(form.start_track_path),
            "endTrackId": remembered(form.end_track_path),
        }

    def remember(self, intent: DJSetIntent) -> None:
        """Store the form a successful generation received, for the next app start."""
        form = PrepFormSettings(
            target_track_count=intent.target_track_count,
            target_minutes=intent.target_minutes,
            strategy=intent.strategy,
            slot_role=intent.slot_role,
            name=intent.name,
            start_track_path=intent.start_path,
            end_track_path=intent.end_path,
        )
        try:
            write_form(self.backend.data_dir, form)
        except OSError as error:
            raise BackendError(
                "settings_unavailable", "App-owned Prep form memory is unavailable; the form was not remembered"
            ) from error
