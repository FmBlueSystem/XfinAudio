"""Bounded manual Live guidance over the exact, freshly verified reviewed set."""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from xfinaudio.application.live_assistance import LiveCandidate, live_session_ready, rank_live_candidates
from xfinaudio.headless.common import BackendError, _public_track
from xfinaudio.headless.serato_safety import opaque_id
from xfinaudio.headless.serato_source import load_source
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation

if TYPE_CHECKING:
    from xfinaudio.headless.backend import HeadlessBackend

LIVE_FIELDS = {
    "live.open": {"reviewId"},
    "live.status": {"sessionId"},
    "live.next": {"sessionId", "revision", "trackId"},
    "live.clear": {"sessionId"},
}


@dataclass(frozen=True)
class LiveSession:
    id: str
    review_id: str
    source_revision: str
    recommendation: PlaylistRecommendation
    revision: int
    played: tuple[str, ...]
    started: tuple[str, ...]
    current_started: float


class LiveGuidance:
    """No playback, provider calls, Serato controls or persistence writes."""

    def __init__(self, backend: HeadlessBackend) -> None:
        self.backend = backend
        self.session: LiveSession | None = None
        self._clock = time.monotonic

    def invalidate(self) -> None:
        self.session = None

    def execute(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if set(params) != LIVE_FIELDS[method]:
            raise BackendError("invalid_params", "Missing or unexpected Live parameters")
        if method == "live.open":
            return self._open(opaque_id(params["reviewId"]))
        session_id = opaque_id(params["sessionId"])
        session = self.session
        if session is None or session.id != session_id:
            raise BackendError("stale_live", "Start local guidance from the current ready review")
        if method == "live.clear":
            self.invalidate()
            return {"cleared": True}
        self._verify(session)
        if method == "live.next":
            revision, track_id = params["revision"], params["trackId"]
            if type(revision) is not int or not 0 <= revision <= 500:
                raise BackendError("invalid_params", "Invalid Live revision")
            if revision != session.revision:
                raise BackendError("stale_live", "The current Live step has changed; refresh the session")
            if not isinstance(track_id, str) or len(track_id) != 64:
                raise BackendError("invalid_params", "Invalid Live track identity")
            candidate = next(
                (item for item in self._ranked(session) if _public_track(item.track)["id"] == track_id), None
            )
            if candidate is None:
                raise BackendError("invalid_live_choice", "Choose one of the freshly eligible next tracks")
            self._verify(session)
            session = replace(
                session,
                revision=session.revision + 1,
                played=(*session.played, candidate.track.path),
                started=(*session.started, datetime.now(UTC).isoformat()),
                current_started=self._clock(),
            )
            self.session = session
        return self._snapshot(session)

    def _ready_source(self, review_id: str):
        review = self.backend.review
        if review is None or self.backend.review_id != review_id or self.backend.review_blocked:
            raise BackendError("live_not_ready", "A current fully ready reviewed set is required")
        source = load_source(self.backend, {"kind": "review", "reviewId": review_id})
        if (
            source.readiness != "ready"
            or source.blockers
            or not live_session_ready(
                review.recommendation,
                review.readiness_report,
                spectral_cohesion=self.backend.preferences.spectral_cohesion(),
            )
        ):
            raise BackendError("live_not_ready", "Resolve all readiness warnings before starting Live guidance")
        return source

    def _open(self, review_id: str) -> dict[str, Any]:
        source = self._ready_source(review_id)
        if (
            self.session is not None
            and self.session.review_id == review_id
            and self.session.source_revision == source.revision
        ):
            self._verify(self.session)
            return self._snapshot(self.session)
        recommendation = source.recommendation
        assert recommendation is not None
        self.session = LiveSession(
            str(uuid4()),
            review_id,
            source.revision,
            recommendation.model_copy(deep=True),
            0,
            (recommendation.ordered_tracks[0].path,),
            (datetime.now(UTC).isoformat(),),
            self._clock(),
        )
        return self._snapshot(self.session)

    def _verify(self, session: LiveSession) -> None:
        try:
            if self._ready_source(session.review_id).revision != session.source_revision:
                raise BackendError("stale_live", "The source changed")
        except BackendError as error:
            self.invalidate()
            raise BackendError("stale_live", "The source changed; start again from a fresh ready review") from error

    def _ranked(self, session: LiveSession) -> list[LiveCandidate]:
        return rank_live_candidates(
            session.recommendation, session.played, spectral_cohesion=self.backend.preferences.spectral_cohesion()
        )

    def _snapshot(self, session: LiveSession) -> dict[str, Any]:
        tracks = {track.path: track for track in session.recommendation.ordered_tracks}
        ranked = self._ranked(session)
        self._verify(session)
        return {
            "sessionId": session.id,
            "revision": session.revision,
            "sourceReviewId": session.review_id,
            "state": "complete" if len(session.played) == len(tracks) else "active",
            "current": _public_track(tracks[session.played[-1]]),
            "history": [
                {"track": _public_track(tracks[path]), "startedAt": started}
                for path, started in zip(session.played[:-1], session.started[:-1], strict=True)
            ],
            "candidates": [
                {
                    "track": _public_track(item.track),
                    "score": item.score.total_score,
                    "alerts": list(item.score.warnings),
                }
                for item in ranked[:5]
            ],
            "elapsedSeconds": max(0.0, self._clock() - session.current_started),
        }
