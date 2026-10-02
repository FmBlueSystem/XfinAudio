"""Opaque saved-set edit sessions, deterministic proposals, and explicit atomic saves."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from xfinaudio.application.playlist_edit_assessment import assess_playlist_edit
from xfinaudio.application.playlist_edit_intents import propose_edit, validate_edit
from xfinaudio.headless.common import BackendError, _inside, _public_track, _text
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_models import Playlist

if TYPE_CHECKING:
    from xfinaudio.headless.backend import HeadlessBackend

EDIT_FIELDS = {
    "playlist.rename": {"playlistId", "name"},
    "playlist.duplicate": {"playlistId"},
    "playlist.edit.open": {"playlistId"},
    "playlist.edit.preview": {"editId", "trackIds", "request"},
    "playlist.edit.save": {"editId", "name", "trackIds"},
    "playlist.edit.discard": {"editId"},
}


def _revision(playlist: Playlist) -> str:
    snapshot = [
        playlist.id,
        playlist.name,
        playlist.created_at.isoformat(),
        playlist.updated_at.isoformat(),
        playlist.track_paths,
    ]
    return hashlib.sha256(json.dumps(snapshot, ensure_ascii=False).encode()).hexdigest()


def _playlist_id(value: Any) -> int:
    if type(value) is not int or not 0 < value <= 2**63 - 1:
        raise BackendError("invalid_params", "Invalid playlist identity")
    return value


@dataclass(frozen=True)
class EditSession:
    edit_id: str
    original: Playlist
    revision: str
    paths_by_id: dict[str, str]


class PlaylistEditor:
    """Single serialized editor session. Draft changes remain in the renderer until Save."""

    def __init__(self, backend: HeadlessBackend) -> None:
        self.backend = backend
        self.session: EditSession | None = None

    def invalidate(self) -> None:
        self.session = None

    def _get(self, playlist_id: int) -> Playlist:
        playlist = self.backend.playlists.get_by_id(playlist_id)
        if playlist is None:
            raise BackendError("not_found", "Playlist was not found")
        return playlist

    def _tracks(self, paths: list[str] | tuple[str, ...]) -> list[dict[str, Any]]:
        records = {track.path: track for track in self.backend._records()}
        result = []
        for path in paths:
            record = records.get(path) or TrackRecord(
                path=path, title=Path(path).stem, missing_required_fields=["bpm", "camelot_key", "energy_level"]
            )
            missing = path not in records or not self._available(path)
            result.append({**_public_track(record), "missing": missing})
        return result

    def _available(self, path: str) -> bool:
        return any(_inside(Path(path), root) for root in self.backend.roots) and Path(path).is_file()

    def _open(self, playlist: Playlist) -> dict[str, Any]:
        tracks = self._tracks(playlist.track_paths)
        session = EditSession(
            str(uuid4()),
            playlist,
            _revision(playlist),
            {track["id"]: path for track, path in zip(tracks, playlist.track_paths, strict=True)},
        )
        self.session = session
        return {
            "editId": session.edit_id,
            "revision": session.revision,
            "id": playlist.id,
            "playlistId": playlist.id,
            "name": playlist.name,
            "tracks": tracks,
            "missingTrackCount": sum(track["missing"] for track in tracks),
        }

    def _current(self, value: Any, *, require_revision: bool = True) -> EditSession:
        try:
            if not isinstance(value, str) or str(UUID(value)) != value:
                raise ValueError
        except (ValueError, AttributeError) as exc:
            raise BackendError("invalid_params", "Invalid edit identity") from exc
        session = self.session
        if session is None or value != session.edit_id:
            raise BackendError("stale_edit", "Open the saved playlist again before editing")
        if require_revision:
            current = self.backend.playlists.get_by_id(_playlist_id(session.original.id))
            if current is None or _revision(current) != session.revision:
                raise BackendError(
                    "stale_edit", "The saved playlist changed; discard this draft and reopen the current version"
                )
        return session

    @staticmethod
    def _paths(session: EditSession, value: Any) -> list[str]:
        if (
            not isinstance(value, list)
            or len(value) > 500
            or any(not isinstance(item, str) or len(item) != 64 for item in value)
        ):
            raise BackendError("invalid_params", "Provide at most 500 valid track identities")
        try:
            paths = [session.paths_by_id[item] for item in value]
        except KeyError as exc:
            raise BackendError("invalid_edit", "A draft cannot add unknown or duplicate tracks.") from exc
        try:
            validate_edit(session.original.track_paths, paths)
        except ValueError as exc:
            raise BackendError("invalid_edit", str(exc)) from exc
        return paths

    @staticmethod
    def _summary(playlist: Playlist) -> dict[str, Any]:
        return {
            "id": playlist.id,
            "name": playlist.name,
            "trackCount": len(playlist.track_paths),
            "updatedAt": playlist.updated_at.isoformat(),
        }

    def execute(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method in ("playlist.rename", "playlist.duplicate", "playlist.edit.open"):
            playlist_id = _playlist_id(params.get("playlistId"))
            # Validate the name before looking up a potentially nonexistent playlist.
            name = _text(params.get("name"), "playlist name") if method == "playlist.rename" else None
            playlist = self._get(playlist_id)
            if method == "playlist.edit.open":
                return self._open(playlist)
            if method == "playlist.rename":
                assert name is not None
                self.backend.saved.rename_playlist(playlist_id, name)
                return self._summary(self._get(playlist_id))
            return self._summary(self.backend.saved.duplicate_playlist(playlist_id))
        session = self._current(params.get("editId"), require_revision=method != "playlist.edit.discard")
        if method == "playlist.edit.discard":
            return self._open(self._get(_playlist_id(session.original.id)))
        paths = self._paths(session, params.get("trackIds"))
        if method == "playlist.edit.save":
            name = _text(params.get("name"), "playlist name")
            saved = self.backend.playlists.compare_and_update(session.original, name=name, track_paths=paths)
            if saved is None:
                raise BackendError(
                    "stale_edit", "The saved playlist changed; discard this draft and reopen the current version"
                )
            return self._open(saved)
        request = _text(params.get("request"), "edit request", 2000)
        records = self.backend._records()
        try:
            proposed = propose_edit(request, paths, records)
            assessment = assess_playlist_edit(proposed, records)
        except ValueError as exc:
            raise BackendError("invalid_edit", str(exc)) from exc
        # Reject a result if an external writer changed the saved version while scoring.
        self._current(session.edit_id)
        return {
            "editId": session.edit_id,
            "previewId": str(uuid4()),
            "revision": session.revision,
            "tracks": self._tracks(proposed),
            "assessment": {
                "description": assessment.description,
                "readiness": assessment.readiness.status,
                "qualityScore": assessment.quality.average_transition_score,
                "warnings": [check.detail for check in assessment.readiness.checks if check.status != "ready"]
                + [warning for score in assessment.recommendation.transition_scores for warning in score.warnings],
            },
        }
