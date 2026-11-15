"""Revision-bound generated-set edits over unchanged deterministic engine helpers."""

from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

from xfinaudio.application.prep_copilot import PrepCopilotVariantApplicationResult
from xfinaudio.exporting.explainability import PlaylistExplanation, build_playlist_explanation
from xfinaudio.headless.common import BackendError, _inside, _public_track
from xfinaudio.headless.review_evidence import evidence
from xfinaudio.headless.review_store import VERSION, clear_review, read_review, write_review
from xfinaudio.headless.serato_safety import opaque_id, source_identity
from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.dj_readiness import DjReadinessReport, build_dj_readiness_report
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport, build_quality_report
from xfinaudio.recommendation.controls import DJControls, preserved_control_paths
from xfinaudio.recommendation.playlist_service import (
    PlaylistRecommendation,
    recommendation_reordered,
    recommendation_with_replacement,
)
from xfinaudio.recommendation.prep_copilot import (
    PrepCopilotPlan,
    PrepVariantName,
    _add_required_track_gate,
    _filter_tracks_for_variant,
)

if TYPE_CHECKING:
    from xfinaudio.headless.backend import HeadlessBackend

LOGGER = logging.getLogger(__name__)

SourceSnapshot = dict[str, tuple[TrackRecord, tuple[object, ...]]]
PlanBinding = tuple[SourceSnapshot, tuple[object, ...]]

REVIEW_FIELDS = {
    "review.details": {"reviewId"},
    "review.resume": set(),
    "review.compare": {"reviewId", "trackId"},
    "review.remove": {"reviewId", "trackId"},
    "review.replace": {"reviewId", "trackId", "replacementId"},
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
        # The replacement each comparison offered, per track, for this exact revision.
        self.offers: dict[str, str | None] = {}
        # True only when a stored review existed but the library no longer matched it.
        self.dropped = False

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
        self.offers.clear()
        self._persist()
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

    def resume(self) -> dict[str, Any]:
        """Report whether a list in progress can be shown, without minting or mutating anything."""
        if self.backend.review is not None and self.review_id is not None:
            try:
                return {"available": True, "review": self.details(), "dropped": False}
            except BackendError:
                # The library moved under the review: nothing weaker is offered instead.
                return {"available": False, "review": None, "dropped": True}
        return {"available": False, "review": None, "dropped": self.dropped}

    def restore(self) -> None:
        """Rebind the review a previous process stored, or drop it honestly."""
        payload = read_review(self.backend.data_dir)
        if payload is None:
            return
        try:
            review = self._decode(payload["review"])
            plan = PrepCopilotPlan.model_validate(payload["plan"])
            if payload["variant"] != review.variant_name:
                raise ValueError("Stored variant does not describe the stored review")
        except (KeyError, TypeError, ValueError):
            LOGGER.warning("The stored list in progress could not be decoded; it is dropped")
            clear_review(self.backend.data_dir)
            return
        sources = self._sources()
        # Restore only when every reviewed track is still the exact library record it was saved with.
        if any(sources.get(track.path, (None,))[0] != track for track in review.recommendation.ordered_tracks):
            LOGGER.warning("The list in progress was dropped because the library changed")
            clear_review(self.backend.data_dir)
            self.dropped = True
            return
        self.backend.plan, self.backend.plan_id = plan, payload["planId"]
        self.sources, self.policy = sources, self._policy()
        # A restored review must compare like the in-memory one: same object as its plan variant.
        variant = next((item for item in plan.variants if item.recommendation == review.recommendation), None)
        if variant is not None:
            review = replace(review, recommendation=variant.recommendation)
        self.backend.review, self.backend.review_id = review, payload["reviewId"]
        self.backend.review_blocked = (
            review.readiness_report.status == "blocked" or not review.recommendation.ordered_tracks
        )
        self.review_id = payload["reviewId"]
        self.removed = frozenset(payload["removed"])
        self.base = {
            "planId": payload["planId"],
            "variants": [dict(item) for item in payload["variants"]],
            "reviewId": payload["reviewId"],
            "name": payload["name"],
            "variant": review.variant_name,
            "tracks": [_public_track(track) for track in review.recommendation.ordered_tracks],
            "warnings": list(payload["warnings"]),
            "blockers": [check.label for check in review.readiness_report.checks if check.status == "blocked"],
            "qualityScore": review.quality_report.average_transition_score,
            "readiness": review.readiness_report.status,
        }
        self.history.clear()
        self.future.clear()
        self.offers.clear()
        # Bind against the library as it is now, so every later edit keeps the stale-source checks.
        self.bind_plan(payload["planId"], (self.sources, self.policy))

    @staticmethod
    def _decode(stored: dict[str, Any]) -> PrepCopilotVariantApplicationResult:
        """Rebuild the application result from the exact models this core writes."""
        return PrepCopilotVariantApplicationResult(
            recommendation=PlaylistRecommendation.model_validate(stored["recommendation"]),
            explanation=PlaylistExplanation.model_validate(stored["explanation"]),
            quality_report=RecommendationQualityReport.model_validate(stored["quality_report"]),
            readiness_report=DjReadinessReport.model_validate(stored["readiness_report"]),
            variant_name=stored["variant_name"],
        )

    def _payload(self) -> dict[str, Any]:
        """Describe the active review exactly as the app-owned recovery file stores it."""
        review, plan = self.backend.review, self.backend.plan
        assert review is not None and plan is not None
        assert self.review_id is not None and self.backend.plan_id is not None
        return {
            "version": VERSION,
            "reviewId": self.review_id,
            "planId": self.backend.plan_id,
            "name": self.base["name"],
            "variant": review.variant_name,
            "warnings": list(self.base["warnings"]),
            "variants": [dict(item) for item in self.base["variants"]],
            "review": {
                "recommendation": review.recommendation.model_dump(mode="json"),
                "explanation": review.explanation.model_dump(mode="json"),
                "quality_report": review.quality_report.model_dump(mode="json"),
                "readiness_report": review.readiness_report.model_dump(mode="json"),
                "variant_name": review.variant_name,
            },
            "plan": plan.model_dump(mode="json"),
            "removed": sorted(self.removed),
        }

    def _persist(self) -> None:
        """Store the review after every change; a refused write never fails the edit it follows."""
        try:
            write_review(self.backend.data_dir, self._payload())
        except (OSError, TypeError, ValueError):
            LOGGER.warning("The list in progress could not be stored; the change stays in memory")

    def clear_stored(self) -> None:
        """Forget the stored review when the backend discards the active one."""
        clear_review(self.backend.data_dir)
        self.dropped = False

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
        # A new revision invalidates every comparison made against the previous one.
        self.offers.clear()
        self.backend.live.invalidate()
        self.backend.invalidate_optional_ai()
        self._persist()

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

    def _offered(
        self, review: PrepCopilotVariantApplicationResult, track_id: Any, replacement_id: Any
    ) -> tuple[str, PlaylistRecommendation]:
        """Apply exactly the replacement the last comparison of this track offered."""
        target, proposed = self._replacement(review, track_id)
        current_paths = {track.path for track in review.recommendation.ordered_tracks}
        replacement = next((track for track in proposed.ordered_tracks if track.path not in current_paths), None)
        if (
            self.offers.get(track_id) is None
            or replacement is None
            or replacement.path != self.offers.get(track_id)
            or _public_track(replacement)["id"] != replacement_id
        ):
            raise BackendError("stale_review", "Compare this track again and use the replacement it offered")
        return target, proposed

    def execute(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if set(params) != REVIEW_FIELDS[method]:
            raise BackendError("invalid_params", "Missing or unexpected generated review fields")
        if method == "review.resume":
            return self.resume()
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
        elif method == "review.replace":
            removed, proposed = self._offered(review, params["trackId"], params["replacementId"])
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
            self.offers[params["trackId"]] = replacement.path if replacement else None
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
