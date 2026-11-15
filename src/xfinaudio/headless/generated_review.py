"""Revision-bound generated-set edits over unchanged deterministic engine helpers."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

from xfinaudio.application.prep_copilot import PrepCopilotVariantApplicationResult
from xfinaudio.exporting.explainability import build_playlist_explanation
from xfinaudio.headless.common import BackendError, _inside, _public_track
from xfinaudio.headless.review_evidence import evidence
from xfinaudio.headless.serato_safety import opaque_id, source_identity
from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.dj_readiness import build_dj_readiness_report
from xfinaudio.quality.recommendation_quality import build_quality_report
from xfinaudio.recommendation.controls import DJControls, preserved_control_paths
from xfinaudio.recommendation.playlist_service import (
    PlaylistRecommendation,
    recommendation_reordered,
    recommendation_with_replacement,
)
from xfinaudio.recommendation.prep_copilot import PrepVariantName, _add_required_track_gate, _filter_tracks_for_variant

if TYPE_CHECKING:
    from xfinaudio.headless.backend import HeadlessBackend

SourceSnapshot = dict[str, tuple[TrackRecord, tuple[object, ...]]]
PlanBinding = tuple[SourceSnapshot, tuple[object, ...]]

REVIEW_FIELDS = {
    "review.details": {"reviewId"},
    "review.compare": {"reviewId", "trackId"},
    "review.remove": {"reviewId", "trackId"},
    "review.reorder": {"reviewId", "trackIds"},
    "review.undo": {"reviewId"},
    "review.redo": {"reviewId"},
}
# One previous state per applied edit; older states fall out of undo reach first.
HISTORY_LIMIT = 50
ReviewState = tuple[PrepCopilotVariantApplicationResult, frozenset[str], dict[str, Any]]


class GeneratedReview:
    def __init__(self, backend: HeadlessBackend) -> None:
        self.backend = backend
        self.review_id: str | None = None
        self.base: dict[str, Any] = {}
        self.sources: dict[str, tuple[TrackRecord, tuple[object, ...]]] = {}
        self.policy: tuple[object, ...] = ()
        self.removed: frozenset[str] = frozenset()
        self.plan_id: str | None = None
        self.plan_binding: PlanBinding | None = None
        self.history: list[ReviewState] = []
        self.future: list[ReviewState] = []

    def _policy(self) -> tuple[object, ...]:
        return self.backend.preferences.spectral_cohesion(), self.backend.preferences.loudness_band()

    def _sources(self) -> dict[str, tuple[TrackRecord, tuple[object, ...]]]:
        result = {}
        for track in self.backend._records():
            path = Path(track.path)
            try:
                if any(_inside(path, root) for root in self.backend.roots):
                    result[track.path] = track, source_identity(path)
            except (OSError, RuntimeError):
                pass
        return result

    def capture_plan(self, records: list[TrackRecord]) -> PlanBinding:
        """Capture the inputs before the engine runs, never on later selection."""
        sources = self._sources()
        if any(sources[track.path][0] != track for track in records if track.path in sources):
            raise BackendError("stale_plan", "Library metadata changed before preparation; regenerate")
        return sources, self._policy()

    def bind_plan(self, plan_id: str, binding: PlanBinding) -> None:
        """Publish only a plan whose complete candidate context is still current."""
        if self._sources() != binding[0] or self._policy() != binding[1]:
            raise BackendError("stale_plan", "Library sources or settings changed during preparation; regenerate")
        self.plan_id, self.plan_binding = plan_id, binding

    def verify_plan(self, plan_id: str) -> None:
        binding = self.plan_binding
        if self.plan_id != plan_id or binding is None or self._sources() != binding[0] or self._policy() != binding[1]:
            raise BackendError("stale_plan", "The generation context changed; generate a current plan")

    def bind(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        """Bind immediately after selecting a generated variant, before publication."""
        self.review_id = self.backend.review_id
        self.base = dict(snapshot)
        assert self.backend.plan_id is not None
        try:
            self.verify_plan(self.backend.plan_id)
        except BackendError:
            self.backend._clear_review()
            self.review_id = None
            raise
        assert self.plan_binding is not None
        self.sources, self.policy = dict(self.plan_binding[0]), self.plan_binding[1]
        self.removed = frozenset()
        self.history.clear()
        self.future.clear()
        return self.details()

    def verify(self, review_id: Any) -> PrepCopilotVariantApplicationResult:
        opaque_id(review_id)
        review = self.backend.review
        if review is None or review_id != self.backend.review_id or review_id != self.review_id:
            raise BackendError("stale_review", "Open a current generated review before continuing")
        current = self._sources()
        if self._policy() != self.policy or any(
            current.get(track.path) != self.sources.get(track.path) or current.get(track.path, (None,))[0] != track
            for track in review.recommendation.ordered_tracks
        ):
            raise BackendError("stale_review", "Review sources or settings changed; prepare a current review")
        return review

    def details(self) -> dict[str, Any]:
        review = self.verify(self.review_id)
        return {
            **self.base,
            **evidence(review, self.backend.plan),
            "canUndo": bool(self.history),
            "canRedo": bool(self.future),
        }

    def _state(self) -> ReviewState:
        review = self.backend.review
        assert review is not None
        return review, self.removed, dict(self.base)

    def _remember(self, states: list[ReviewState]) -> None:
        states.append(self._state())
        while len(states) > HISTORY_LIMIT:
            del states[0]

    def _publish(
        self, review: PrepCopilotVariantApplicationResult, removed: frozenset[str], base: dict[str, Any]
    ) -> None:
        """Republish one applied state under a fresh revision, exactly like an edit."""
        self.backend.review = review
        self.backend.review_id = str(uuid4())
        self.review_id = self.backend.review_id
        self.removed = removed
        self.base = {
            **base,
            "reviewId": self.review_id,
            "tracks": [_public_track(track) for track in review.recommendation.ordered_tracks],
            "qualityScore": review.quality_report.average_transition_score,
            "readiness": review.readiness_report.status,
            "blockers": [check.label for check in review.readiness_report.checks if check.status == "blocked"],
        }
        self.backend.review_blocked = (
            review.readiness_report.status == "blocked" or not review.recommendation.ordered_tracks
        )
        self.backend.live.invalidate()
        self.backend.invalidate_optional_ai()

    def _travel(self, *, back: bool) -> dict[str, Any]:
        source, target = (self.history, self.future) if back else (self.future, self.history)
        if not source:
            raise BackendError(
                "nothing_to_undo", "Nothing to undo in this review" if back else "Nothing to redo in this review"
            )
        state = source[-1]
        # A refused travel must not republish anything, and it must not resurrect a
        # track whose source changed after the edit that stored this state.
        current = self._sources()
        if any(
            current.get(track.path) != self.sources.get(track.path) for track in state[0].recommendation.ordered_tracks
        ):
            raise BackendError("stale_review", "Restored sources changed; prepare a current review")
        source.pop()
        self._remember(target)
        self._publish(*state)
        return self.details()

    def _assess(self, recommendation: PlaylistRecommendation) -> PrepCopilotVariantApplicationResult:
        current, plan = self.backend.review, self.backend.plan
        assert current is not None and plan is not None
        quality = build_quality_report(recommendation)
        readiness = _add_required_track_gate(
            build_dj_readiness_report(recommendation, quality), recommendation, plan.intent
        )
        return replace(
            current,
            recommendation=recommendation,
            explanation=build_playlist_explanation(recommendation),
            quality_report=quality,
            readiness_report=readiness,
        )

    def _replacement(
        self, review: PrepCopilotVariantApplicationResult, track_id: Any
    ) -> tuple[str, PlaylistRecommendation]:
        recommendation, plan = review.recommendation, self.backend.plan
        assert plan is not None
        target = next(
            (track.path for track in recommendation.ordered_tracks if _public_track(track)["id"] == track_id), None
        )
        if target is None:
            raise BackendError("invalid_params", "Choose a track in the current generated set")
        controls = DJControls.model_validate(recommendation.applied_controls)
        if target in preserved_control_paths(controls) | set(plan.intent.required_paths):
            raise BackendError("protected_track", "This track is protected by the set controls")
        current = self._sources()
        candidates = [
            track for path, (track, identity) in current.items() if self.sources.get(path) == (track, identity)
        ]
        candidates, _ = _filter_tracks_for_variant(cast(PrepVariantName, review.variant_name), candidates, plan.intent)
        proposed = recommendation_with_replacement(
            recommendation,
            target,
            candidates,
            spectral_cohesion=self.backend.preferences.spectral_cohesion(),
            locked_paths=frozenset(plan.intent.required_paths),
            excluded_paths=frozenset(plan.intent.excluded_paths) | self.removed,
            loudness_band=self.backend.preferences.loudness_band(),
        )
        after = self._sources()
        if any(after.get(track.path) != current.get(track.path) for track in proposed.ordered_tracks):
            raise BackendError("stale_review", "Replacement sources changed; prepare a current review")
        return target, proposed

    def execute(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if set(params) != REVIEW_FIELDS[method]:
            raise BackendError("invalid_params", "Missing or unexpected generated review fields")
        review = self.verify(params["reviewId"])
        if method == "review.details":
            return self.details()
        if method in ("review.undo", "review.redo"):
            return self._travel(back=method == "review.undo")
        removed = None
        if method == "review.reorder":
            ids = params["trackIds"]
            tracks = {_public_track(track)["id"]: track for track in review.recommendation.ordered_tracks}
            if (
                not isinstance(ids, list)
                or any(not isinstance(item, str) for item in ids)
                or len(ids) != len(tracks)
                or set(ids) != set(tracks)
            ):
                raise BackendError("invalid_params", "Reorder requires each current track exactly once")
            paths = [tracks[item].path for item in ids]
            controls = DJControls.model_validate(review.recommendation.applied_controls)
            prefix = [path for path in controls.manual_order_paths if path in paths]
            if (
                (controls.start_path in paths and paths[0] != controls.start_path)
                or (controls.end_path in paths and paths[-1] != controls.end_path)
                or paths[: len(prefix)] != prefix
            ):
                raise BackendError(
                    "protected_track", "Reordering must preserve opening, closing and manual control order"
                )
            proposed = recommendation_reordered(
                review.recommendation, paths, spectral_cohesion=self.backend.preferences.spectral_cohesion()
            )
        else:
            removed, proposed = self._replacement(review, params["trackId"])
        assessed = self._assess(proposed)
        self.verify(params["reviewId"])
        current_sources = self._sources()
        if any(current_sources.get(track.path) != self.sources.get(track.path) for track in proposed.ordered_tracks):
            raise BackendError("stale_review", "Proposed sources changed; prepare a current review")
        if method == "review.compare":
            current_paths = {track.path for track in review.recommendation.ordered_tracks}
            replacement = next((track for track in proposed.ordered_tracks if track.path not in current_paths), None)
            return {
                "reviewId": self.review_id,
                "replacement": _public_track(replacement) if replacement else None,
                "available": replacement is not None,
                "original": {"qualityScore": review.quality_report.average_transition_score, **evidence(review, None)},
                "proposed": {
                    "qualityScore": assessed.quality_report.average_transition_score,
                    **evidence(assessed, None),
                },
                "message": "Preview only; nothing has been applied."
                if replacement
                else "No eligible replacement passed the current constraints. Removing will shorten the set.",
            }
        # Only an applied edit becomes history; a refused or stale one leaves the stacks untouched.
        self._remember(self.history)
        self.future.clear()
        self._publish(
            assessed,
            self.removed | {removed} if removed is not None else self.removed,
            {
                **self.base,
                "warnings": list(dict.fromkeys([*self.base["warnings"], *proposed.warnings])),
            },
        )
        return self.details()
