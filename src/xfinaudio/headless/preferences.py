"""Bounded app-owned preferences; write-capable legacy services stay uncomposed."""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import re
import stat
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from xfinaudio.config.settings import AiSettings, AppSettings
from xfinaudio.config.settings_repository import InvalidSettingsError, SettingsRepository, SettingsRepositoryError
from xfinaudio.headless.common import BackendError
from xfinaudio.recommendation.loudness_policy import LoudnessBand

if TYPE_CHECKING:
    from xfinaudio.headless.backend import HeadlessBackend

SETTINGS_FIELDS = {"settings.get": set(), "settings.update": {"revision", "previewVolume", "watchLibrary"}}
MAX_SETTINGS_BYTES = 256 * 1024


def _read(path: Path) -> tuple[bytes | None, str]:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None, hashlib.sha256(b"\x00missing").hexdigest()
    with os.fdopen(descriptor, "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_SETTINGS_BYTES:
            raise OSError("Unsafe or oversized app-owned settings")
        content = handle.read(MAX_SETTINGS_BYTES + 1)
        after = os.fstat(handle.fileno())
        if len(content) > MAX_SETTINGS_BYTES or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise OSError("Settings changed during reading")
        return content, hashlib.sha256(b"\x01" + content).hexdigest()


class BoundedSettingsRepository(SettingsRepository):
    """Retain existing save/recovery semantics with a confined, bounded loader."""

    read_signature = ""

    def load(self) -> AppSettings:
        try:
            content, self.read_signature = _read(self.settings_path)
        except OSError as error:
            raise SettingsRepositoryError("App-owned preferences cannot be read safely") from error
        if content is None:
            return AppSettings()
        try:
            payload = json.loads(content)
            if not isinstance(payload, dict):
                raise ValueError("Unsupported settings shape")
            return AppSettings.model_validate(payload)
        except (ValueError, UnicodeError, ValidationError) as error:
            raise InvalidSettingsError("Invalid app-owned preferences") from error


class PreferencesService:
    def __init__(self, backend: HeadlessBackend) -> None:
        self.backend = backend
        self.repository = BoundedSettingsRepository(backend.data_dir / "settings.json")
        self.settings: AppSettings | None = None
        self.revision = ""
        self.recovered = False

    @contextmanager
    def _lock(self):
        descriptor = os.open(
            self.backend.data_dir / ".settings.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600
        )
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise OSError("Unsafe settings lock")
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            os.close(descriptor)

    def _load(self) -> None:
        _, signature = _read(self.repository.settings_path)
        if self.settings is not None and signature == self.revision:
            return
        loaded = self.repository.load_with_recovery()
        content, after = _read(self.repository.settings_path)
        recovered = bool(self.repository.recovery_warning)
        if after != self.repository.read_signature and not (recovered and content is None):
            raise BackendError("stale_settings", "Preferences changed while loading; refresh them")
        self.settings, self.revision, self.recovered = loaded, after, recovered

    def execute(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if set(params) != SETTINGS_FIELDS[method]:
            raise BackendError("invalid_params", "Missing or unexpected preference fields")
        if method == "settings.update":
            volume, watch, revision = params["previewVolume"], params["watchLibrary"], params["revision"]
            if (
                type(volume) not in (int, float)
                or not 0 <= volume <= 1
                or not math.isfinite(volume)
                or type(watch) is not bool
                or not isinstance(revision, str)
                or re.fullmatch(r"[0-9a-f]{64}", revision) is None
            ):
                raise BackendError("invalid_params", "Invalid preference value or revision")
        try:
            with self._lock():
                self._load()
                assert self.settings is not None
                if method == "settings.update":
                    if params["revision"] != self.revision:
                        raise BackendError("stale_settings", "Preferences changed; refresh before saving")
                    updated = self.settings.model_copy(
                        update={
                            "audio": self.settings.audio.model_copy(
                                update={"preview_volume": float(params["previewVolume"])}
                            ),
                            "library": self.settings.library.model_copy(
                                update={"watch_for_changes": params["watchLibrary"]}
                            ),
                        }
                    )
                    self._save(updated)
                return self._public()
        except (OSError, SettingsRepositoryError) as error:
            raise BackendError(
                "settings_unavailable", "App-owned preferences are unavailable; no settings were applied"
            ) from error

    def _save(self, updated: AppSettings) -> None:
        """Commit under the shared settings lock only while the revision is current."""
        if _read(self.repository.settings_path)[1] != self.revision:
            raise BackendError("stale_settings", "Preferences changed before saving")
        self.repository.save(updated)
        self.settings, self.revision, self.recovered = updated, _read(self.repository.settings_path)[1], False

    def get_profiles(self) -> dict[str, Any]:
        """Read the original scoring preference without probing audio engines."""
        return self._profiles_access()

    def spectral_cohesion(self) -> float:
        return self.get_profiles()["spectralCohesion"]

    def update_profiles(self, params: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(params, dict) or set(params) != {"revision", "spectralCohesion"}:
            raise BackendError("invalid_params", "Missing or unexpected profile preference fields")
        value, revision = params["spectralCohesion"], params["revision"]
        if (
            type(value) not in (int, float)
            or not 0 <= value <= 1
            or not math.isfinite(value)
            or not isinstance(revision, str)
            or re.fullmatch(r"[0-9a-f]{64}", revision) is None
        ):
            raise BackendError("invalid_params", "Invalid spectral cohesion or preference revision")
        return self._profiles_access(params)

    def _profiles_access(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            with self._lock():
                self._load()
                assert self.settings is not None
                if params is not None:
                    if params["revision"] != self.revision:
                        raise BackendError("stale_settings", "Preferences changed; refresh before saving")
                    scoring = self.settings.scoring.model_copy(
                        update={"spectral_cohesion": float(params["spectralCohesion"])}
                    )
                    self._save(self.settings.model_copy(update={"scoring": scoring}))
                return {"revision": self.revision, "spectralCohesion": self.settings.scoring.spectral_cohesion}
        except (OSError, SettingsRepositoryError) as error:
            raise BackendError(
                "settings_unavailable", "App-owned preferences are unavailable; no settings were applied"
            ) from error

    def get_loudness(self) -> dict[str, Any]:
        """Read the original single-switch policy through the bounded settings flow."""
        return self._loudness_access()

    def update_loudness(self, params: dict[str, Any]) -> dict[str, Any]:
        """Update only the complete revision-bound loudness policy."""
        if not isinstance(params, dict) or set(params) != {"revision", "enabled", "targetLufs", "toleranceLu"}:
            raise BackendError("invalid_params", "Missing or unexpected loudness preference fields")
        target, tolerance, revision = params["targetLufs"], params["toleranceLu"], params["revision"]
        if (
            type(params["enabled"]) is not bool
            or type(target) not in (int, float)
            or not -30 <= target <= 0
            or not math.isfinite(target)
            or type(tolerance) not in (int, float)
            or not 0 <= tolerance <= 10
            or not math.isfinite(tolerance)
            or not isinstance(revision, str)
            or re.fullmatch(r"[0-9a-f]{64}", revision) is None
        ):
            raise BackendError("invalid_params", "Invalid loudness preference value or revision")
        return self._loudness_access(params)

    def _loudness_access(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            with self._lock():
                self._load()
                assert self.settings is not None
                if params is not None:
                    if params["revision"] != self.revision:
                        raise BackendError("stale_settings", "Preferences changed; refresh before saving")
                    loudness = self.settings.loudness.model_copy(
                        update={
                            "enabled": params["enabled"],
                            "target_lufs": float(params["targetLufs"]),
                            "tolerance_lu": float(params["toleranceLu"]),
                        }
                    )
                    self._save(self.settings.model_copy(update={"loudness": loudness}))
                return {
                    "revision": self.revision,
                    "enabled": self.settings.loudness.enabled,
                    "targetLufs": self.settings.loudness.target_lufs,
                    "toleranceLu": self.settings.loudness.tolerance_lu,
                }
        except (OSError, SettingsRepositoryError) as error:
            raise BackendError(
                "settings_unavailable", "App-owned preferences are unavailable; no settings were applied"
            ) from error

    def loudness_band(self) -> LoudnessBand:
        """Return the configured domain policy, independently of analysis scheduling."""
        snapshot = self.get_loudness()
        return LoudnessBand(snapshot["targetLufs"], snapshot["toleranceLu"])

    def get_ai(self) -> dict[str, Any]:
        """Expose selection state only, without credential or environment discovery."""
        return self._ai_access()[0]

    @staticmethod
    def _validate_ai_fields(params: dict[str, Any], field: str) -> None:
        if (
            not isinstance(params, dict)
            or set(params) != {"revision", field}
            or not isinstance(params["revision"], str)
            or re.fullmatch(r"[0-9a-f]{64}", params["revision"]) is None
        ):
            raise BackendError("invalid_params", "Invalid AI preference fields or revision")

    def update_ai(self, params: dict[str, Any]) -> dict[str, Any]:
        """Persist the explicit enable choice and optional automatic authorization."""
        allowed = {"revision", "enabled", "autoAuthorize"}
        if (
            not isinstance(params, dict)
            or not set(params) <= allowed
            or not {"revision", "enabled"} <= set(params)
            or not isinstance(params["revision"], str)
            or re.fullmatch(r"[0-9a-f]{64}", params["revision"]) is None
        ):
            raise BackendError("invalid_params", "Invalid AI preference fields or revision")
        if type(params["enabled"]) is not bool:
            raise BackendError("invalid_params", "Invalid AI enabled preference")
        if "autoAuthorize" in params and type(params["autoAuthorize"]) is not bool:
            raise BackendError("invalid_params", "Invalid AI automatic-authorization preference")
        return self._ai_access(params)[0]

    def set_ai_credential(self, params: dict[str, Any]) -> dict[str, Any]:
        """Trusted-core selection only: never read, probe or modify the selected path."""
        self._validate_ai_fields(params, "path")
        path = params["path"]
        if path is not None and (
            not isinstance(path, Path) or not path.is_absolute() or len(str(path)) > 4096 or "\x00" in str(path)
        ):
            raise BackendError("invalid_params", "Select an absolute credential file path")
        return self._ai_access(params)[0]

    def ai_settings(self) -> AiSettings:
        """Return the original immutable settings for later explicitly requested work."""
        return self._ai_access()[1]

    def _ai_access(self, params: dict[str, Any] | None = None) -> tuple[dict[str, Any], AiSettings]:
        try:
            with self._lock():
                self._load()
                assert self.settings is not None
                if params is not None:
                    if params["revision"] != self.revision:
                        raise BackendError("stale_settings", "Preferences changed; refresh before saving")
                    if "path" in params:
                        changes = {"env_file": params["path"]}
                    else:
                        # Settings save: the UI sends enabled and may toggle the
                        # persisted automatic authorization in the same request;
                        # absent means keep the persisted value.
                        changes = {
                            "enabled": params["enabled"],
                            # Model field name is snake_case; the protocol key is
                            # camelCase (autoAuthorize) and maps here.
                            "auto_authorize": params.get("autoAuthorize", self.settings.ai.auto_authorize),
                        }
                    self._save(self.settings.model_copy(update={"ai": self.settings.ai.model_copy(update=changes)}))
                settings = self.settings.ai
                label = None
                if settings.env_file is not None:
                    label = "".join(
                        char for char in settings.env_file.name if char.isprintable() and char not in "/\\"
                    )[:200]
                    label = label or "Archivo seleccionado"
                return (
                    {
                        "revision": self.revision,
                        "enabled": settings.enabled,
                        "autoAuthorize": settings.auto_authorize,
                        "provider": settings.provider,
                        "credentialLabel": label,
                        "configured": settings.env_file is not None,
                    },
                    settings,
                )
        except (OSError, SettingsRepositoryError) as error:
            raise BackendError(
                "settings_unavailable", "App-owned preferences are unavailable; no settings were applied"
            ) from error

    def _public(self) -> dict[str, Any]:
        assert self.settings is not None
        return {
            "revision": self.revision,
            "previewVolume": self.settings.audio.preview_volume,
            "watchLibrary": self.settings.library.watch_for_changes,
            "recoveryWarning": self.recovered,
            "libraryLabels": [
                "".join(char for char in root.name if char.isprintable())[:200] or "Carpeta raíz"
                for root in self.backend.roots
            ],
            "capabilities": {"loudnessWriteback": True, "providers": True, "language": "es"},
        }
