"""Explicit persistent Prep controls using original app-owned BuildSessionSettings."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from xfinaudio.config.settings import BuildSessionSettings
from xfinaudio.config.settings_repository import SettingsRepositoryError
from xfinaudio.headless.common import BackendError, _inside, _public_track

if TYPE_CHECKING:
    from xfinaudio.headless.backend import HeadlessBackend

PREP_SETTINGS_FIELDS = {
    "prep.settings.get": set(),
    "prep.settings.update": {"revision", "requiredTrackIds", "excludedTrackIds", "genreFocus", "clearUnavailable"},
}


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
                return {
                    "revision": preferences.revision,
                    "requiredTrackIds": sorted(ids[path] for path in build.locked_paths if path in ids),
                    "excludedTrackIds": sorted(ids[path] for path in build.excluded_paths if path in ids),
                    "genreFocus": build.genre_focus or "",
                    "unavailableRequiredCount": len(build.locked_paths - ids.keys()),
                    "unavailableExcludedCount": len(build.excluded_paths - ids.keys()),
                }
        except (OSError, SettingsRepositoryError) as error:
            raise BackendError(
                "settings_unavailable", "App-owned Prep preferences are unavailable; no settings were applied"
            ) from error
