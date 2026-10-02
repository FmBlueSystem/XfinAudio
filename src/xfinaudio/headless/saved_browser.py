"""Local saved-set search, comparison, and exact-snapshot recoverable removal."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from xfinaudio.application.playlist_recovery import PlaylistRecovery
from xfinaudio.application.saved_playlist_assistant import compare_saved_sets, search_saved_sets
from xfinaudio.headless.common import BackendError
from xfinaudio.headless.playlist_editor import PlaylistEditor, _playlist_id, _revision
from xfinaudio.library.playlist_models import Playlist

if TYPE_CHECKING:
    from xfinaudio.headless.backend import HeadlessBackend

SAVED_FIELDS = {
    "playlist.search": {"request"},
    "playlist.compare": {"playlistIds"},
    "playlist.delete.preview": {"playlistId"},
    "playlist.delete.commit": {"previewId", "confirmed"},
    "playlist.deleted.list": set(),
    "playlist.restore": {"deletionId"},
}


def _token(value: Any) -> str:
    try:
        if not isinstance(value, str) or str(UUID(value)) != value:
            raise ValueError
    except (ValueError, AttributeError) as exc:
        raise BackendError("invalid_params", "Invalid recovery identity") from exc
    return value


class SavedBrowser:
    def __init__(self, backend: HeadlessBackend) -> None:
        self.backend = backend
        self.recovery = PlaylistRecovery(backend.playlists.db_path)
        self.preview: tuple[str, Playlist] | None = None

    def _get(self, value: Any) -> Playlist:
        playlist = self.backend.playlists.get_by_id(_playlist_id(value))
        if playlist is None:
            raise BackendError("not_found", "Saved playlist was not found")
        return playlist

    def execute(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method not in SAVED_FIELDS or set(params) - SAVED_FIELDS[method]:
            raise BackendError("invalid_params", "Unexpected saved-set parameters")
        try:
            return self._execute(method, params)
        except (sqlite3.Error, OSError, ValueError, KeyError, TypeError) as exc:
            raise BackendError(
                "recovery_failed", "Saved playlist operation failed; existing data was retained"
            ) from exc

    def _execute(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method == "playlist.search":
            request = params.get("request", "")
            if not isinstance(request, str) or len(request) > 2000 or "\x00" in request:
                raise BackendError("invalid_params", "Invalid saved-set search")
            playlists = [self._get(p.id) for p in self.backend.playlists.list_summaries()]
            matches = search_saved_sets(request, playlists, self.backend._records())
            return {"playlists": [PlaylistEditor._summary(p) for p in matches]}
        if method == "playlist.compare":
            ids = params.get("playlistIds")
            if not isinstance(ids, list) or not 2 <= len(ids) <= 200:
                raise BackendError("invalid_params", "Select 2–200 saved playlists")
            validated = [_playlist_id(value) for value in ids]
            if len(set(validated)) != len(validated):
                raise BackendError("invalid_params", "Select distinct saved playlists")
            return {
                "comparison": compare_saved_sets([self._get(value) for value in validated], self.backend._records())
            }
        if method == "playlist.delete.preview":
            playlist = self._get(params.get("playlistId"))
            identity = str(uuid4())
            self.preview = identity, playlist
            return {
                "previewId": identity,
                "playlistId": playlist.id,
                "revision": _revision(playlist),
                "name": playlist.name,
                "trackCount": len(playlist.track_paths),
            }
        if method == "playlist.delete.commit":
            identity = _token(params.get("previewId"))
            if params.get("confirmed") is not True:
                raise BackendError("confirmation_required", "Confirm removal in the native dialog")
            preview, self.preview = self.preview, None
            if preview is None or preview[0] != identity:
                raise BackendError("stale_delete", "Request removal again for the current saved playlist")
            deletion_id = self.recovery.archive(preview[1])
            if deletion_id is None:
                raise BackendError("stale_delete", "The saved playlist changed; request removal again")
            self.backend.editor.invalidate()
            self.backend.invalidate_optional_ai()
            return {"deletionId": deletion_id, "name": preview[1].name}
        if method == "playlist.deleted.list":
            return {"playlists": self.recovery.list_deleted()}
        identity = _token(params.get("deletionId"))
        restored_id = self.recovery.restore(identity)
        if restored_id is None:
            raise BackendError("not_found", "This saved playlist is unavailable or already restored")
        self.backend.invalidate_optional_ai()
        return PlaylistEditor._summary(self._get(restored_id))
