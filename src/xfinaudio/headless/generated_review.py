"""Revision-bound generated-set edits over unchanged deterministic engine helpers."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

from xfinaudio.application.prep_copilot import PrepCopilotVariantApplicationResult
from xfinaudio.exporting.explainability import PlaylistExplanation, build_playlist_explanation
from xfinaudio.headless.ai_conversation import applied_changes
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
    insertion_positions,
    known_release_year,
    recommendation_extended,
    recommendation_fitted,
    recommendation_inserted,
    recommendation_reordered,
    recommendation_swapped,
    recommendation_with_replacement,
    recommendation_without_paths,
    rewrite_shortfall_warnings,
)
from xfinaudio.recommendation.prep_copilot import (
    PrepCopilotPlan,
    PrepVariantName,
    _add_required_track_gate,
    _filter_tracks_for_variant,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from xfinaudio.headless.backend import HeadlessBackend

LOGGER = logging.getLogger(__name__)

SourceEntry = tuple[TrackRecord, tuple[object, ...] | None]
SourceSnapshot = dict[str, SourceEntry]
PlanBinding = tuple[SourceSnapshot, tuple[object, ...]]

REVIEW_FIELDS = {
    "review.details": {"reviewId"},
    "review.resume": set(),
    "review.compare": {"reviewId", "trackId"},
    "review.drop": {"reviewId", "trackId"},
    "review.insert": {"reviewId", "trackId", "position"},
    "review.remove": {"reviewId", "trackId"},
    "review.replace": {"reviewId", "trackId", "replacementId"},
    "review.reorder": {"reviewId", "trackIds"},
    "review.swap": {"reviewId", "trackId", "replacementTrackId"},
    "review.extend": {"reviewId", "targetTrackCount"},
    "review.fit_period": {"reviewId", "yearMin", "yearMax"},
    "review.undo": {"reviewId"},
    "review.redo": {"reviewId"},
}
# One previous state per applied edit; older states fall out of undo reach first.
HISTORY_LIMIT = 50
# The longest list an edit may grow a review to, matching the intent's own target cap.
MAX_EXTENDED_TRACK_COUNT = 100
# An edit that would leave fewer tracks than this in the list is refused, never applied.
MIN_REVIEW_TRACK_COUNT = 2
# The calendar years a period edit may name, both ends included.
MIN_PERIOD_YEAR = 1900
MAX_PERIOD_YEAR = 2100
ReviewState = tuple[PrepCopilotVariantApplicationResult, frozenset[str], dict[str, Any]]


class GeneratedReview:
    def __init__(self, backend: HeadlessBackend) -> None:
        self.backend = backend
        self.review_id: str | None = None
        self.base: dict[str, Any] = {}
        self.sources: dict[str, SourceEntry] = {}
        self.policy: tuple[object, ...] = ()
        self.removed: frozenset[str] = frozenset()
        self.plan_id: str | None = None
        self.plan_binding: PlanBinding | None = None
        self.history: list[ReviewState] = []
        self.future: list[ReviewState] = []
        # The replacement each comparison offered, per track, for this exact revision.
        self.offers: dict[str, str | None] = {}
        # One core command reads the library sources at most twice: the snapshot taken at
        # its start and the refreshed one its final check takes. Outside a command every
        # read is fresh, so a plan binding and the scan keep their independent reads.
        self._snapshot: SourceSnapshot | None = None
        # The paths whose identity that snapshot already read; ``None`` means the whole
        # library, and each further guard fills in only the tracks it needs.
        self._fresh: set[str] | None = None
        self._refreshed = False
        self._scope_depth = 0
        # True only when a stored review existed but the library no longer matched it.
        self.dropped = False

    def _policy(self) -> tuple[object, ...]:
        return self.backend.preferences.spectral_cohesion(), self.backend.preferences.loudness_band()

    @contextmanager
    def snapshot_scope(self) -> Iterator[None]:
        """Share one library source snapshot for the length of one core command.

        Every guard the command makes reads the snapshot it already has; only the
        command's final check reads the identities it already read once more, so a change
        made during the command is still noticed without re-reading the whole library for
        each guard.
        """
        self._scope_depth += 1
        try:
            yield
        finally:
            self._scope_depth -= 1
            if not self._scope_depth:
                self._snapshot, self._fresh, self._refreshed = None, None, False

    def _sources(self, checked: frozenset[str] | None = None, *, final: bool = False) -> SourceSnapshot:
        """The library source snapshot, built at most twice inside one command.

        ``checked`` names the tracks whose on-disk identity the caller acts on: only those
        are read from disk, and every other library track contributes its stored record
        without touching it. ``None`` checks the whole library, as a plan binding does.
        ``final`` asks for the command's final check: the identities already read are
        read once more, so a change made during the command is still noticed.

        One command keeps one snapshot and fills it path by path, so a guard that needs a
        track the command has not read yet reads that track instead of the whole library.
        """
        wanted = None if checked is None else frozenset(checked)
        if not self._scope_depth:
            return self._build_sources(wanted)
        if self._snapshot is None:
            self._snapshot = self._build_sources(wanted)
            self._fresh, self._refreshed = (None if wanted is None else set(wanted)), final
            return self._snapshot
        requested = frozenset(self._snapshot) if wanted is None else wanted
        refresh = final and not self._refreshed
        if self._fresh is None:
            read = requested if refresh else frozenset()
        else:
            read = (requested - self._fresh) | (self._fresh if refresh else frozenset())
        if read:
            current = self._build_sources(read)
            for path in read:
                if path in current:
                    self._snapshot[path] = current[path]
                else:
                    # A moved, deleted or unreadable source is absent, never trusted.
                    self._snapshot.pop(path, None)
            if self._fresh is not None:
                self._fresh |= read
        self._refreshed = self._refreshed or final
        return self._snapshot

    def _build_sources(self, checked: frozenset[str] | None, *, unread: bool = False) -> SourceSnapshot:
        """Read the library sources exactly as they are now, for the ``checked`` paths.

        Only the ``checked`` paths are read from disk; every other library track
        contributes its stored record and the identity the generation recorded, so a
        review command never re-checks a track it does not act on. The result belongs to
        the caller: one command copies the entries it asked for into its own snapshot.

        ``unread`` keeps every unlisted library track even before this review recorded
        anything about it, with its stored record and no identity: that is the whole
        library a restart restores, without reading the disk of the tracks it does not
        list.
        """
        result = {}
        for track in self.backend._records(checked=checked):
            path = Path(track.path)
            try:
                if not any(_inside(path, root) for root in self.backend.roots):
                    continue
                if checked is not None and track.path not in checked:
                    stored = self.sources.get(track.path)
                    if stored is not None:
                        result[track.path] = track, stored[1]
                    elif unread:
                        result[track.path] = track, None
                    continue
                result[track.path] = track, source_identity(path)
            except (OSError, RuntimeError):
                pass
        return result

    @staticmethod
    def _same(recorded: SourceEntry | None, current: SourceEntry | None) -> bool:
        """Whether one track is still exactly what this review recorded.

        A restored review reads the disk identity only of the tracks its list holds and
        keeps every other library track with the record the scan stored, so where no
        identity was recorded the record alone decides and the fresh read is the one the
        command acts on.
        """
        if recorded is None or current is None:
            return False
        return recorded[0] == current[0] and (recorded[1] is None or recorded[1] == current[1])

    @classmethod
    def _unchanged(cls, recorded: SourceSnapshot, current: SourceSnapshot) -> bool:
        """Whether every recorded track is still what it was, and no track left the library."""
        return set(recorded) == set(current) and all(cls._same(recorded[path], current[path]) for path in recorded)

    def _reverify(self, recorded: SourceSnapshot) -> SourceSnapshot:
        """Re-read a snapshot the way it was recorded: only where it recorded an identity.

        A generation snapshot covers the whole library, so its verification reads the whole
        library, and a track that appeared since is still a change. A restart records
        identities only for the tracks its list holds, so its verification reads those and
        keeps every other library track with the record the scan stored.
        """
        checked = frozenset(path for path, entry in recorded.items() if entry[1] is not None)
        return self._build_sources(checked, unread=True)

    def capture_plan(self, records: list[TrackRecord]) -> PlanBinding:
        """Capture the inputs before the engine runs, never on later selection."""
        sources = self._sources()
        if any(sources[track.path][0] != track for track in records if track.path in sources):
            raise BackendError("stale_plan", "Library metadata changed before preparation; regenerate")
        return sources, self._policy()

    def bind_plan(self, plan_id: str, binding: PlanBinding) -> None:
        """Publish only a plan whose complete candidate context is still current."""
        if not self._unchanged(binding[0], self._reverify(binding[0])) or self._policy() != binding[1]:
            raise BackendError("stale_plan", "Library sources or settings changed during preparation; regenerate")
        self.plan_id, self.plan_binding = plan_id, binding

    def verify_plan(self, plan_id: str) -> None:
        binding = self.plan_binding
        if (
            self.plan_id != plan_id
            or binding is None
            or not self._unchanged(binding[0], self._reverify(binding[0]))
            or self._policy() != binding[1]
        ):
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

    @staticmethod
    def _paths(review: PrepCopilotVariantApplicationResult) -> frozenset[str]:
        """The tracks this review's list holds: the ones every edit acts on."""
        return frozenset(track.path for track in review.recommendation.ordered_tracks)

    def verify(self, review_id: Any) -> PrepCopilotVariantApplicationResult:
        opaque_id(review_id)
        review = self.backend.review
        if review is None or review_id != self.backend.review_id or review_id != self.review_id:
            raise BackendError("stale_review", "Open a current generated review before continuing")
        current = self._sources(self._paths(review))
        if self._policy() != self.policy or any(
            not self._same(self.sources.get(track.path), current.get(track.path))
            or current.get(track.path, (None,))[0] != track
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
        sources = self._build_sources(self._paths(review), unread=True)
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
        # Bind against the library as it is now, so every later edit keeps the stale-source
        # checks. The binding re-reads the tracks the list holds and no other one, so a
        # change made while restoring is still refused.
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
        previous = self.backend.review
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
        # The conversation remembers what each applied change did to the list, so its next
        # turn can tell the assistant what changed. Only the two lists are compared: no
        # path and no track identity ever enters that memory.
        if previous is not None:
            self.backend.ai_conversation.note_applied(
                applied_changes(previous.recommendation.ordered_tracks, review.recommendation.ordered_tracks)
            )
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
        state_paths = self._paths(state[0])
        current = self._sources(state_paths, final=True)
        if any(
            not self._same(self.sources.get(track.path), current.get(track.path))
            for track in state[0].recommendation.ordered_tracks
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
        target = self._listed(review, track_id)
        if target in self._protected(review):
            raise BackendError("protected_track", "This track is protected by the set controls")
        current = self._sources(frozenset())
        candidates = [entry[0] for path, entry in current.items() if self._same(self.sources.get(path), entry)]
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
        # The command's own final check re-reads the disk identity of every track this
        # proposal would put in the list, so a candidate that changed while it was being
        # chosen is refused there with the same code as before.
        return target, proposed

    def _listed(self, review: PrepCopilotVariantApplicationResult, track_id: Any) -> str:
        """The path of a track this review's list holds, or the edit's own refusal."""
        path = next(
            (track.path for track in review.recommendation.ordered_tracks if _public_track(track)["id"] == track_id),
            None,
        )
        if path is None:
            raise BackendError("invalid_params", "Choose a track in the current generated set")
        return path

    def _protected(self, review: PrepCopilotVariantApplicationResult) -> set[str]:
        """The tracks this review must never take out, exactly as every edit reads them."""
        plan = self.backend.plan
        assert plan is not None
        controls = DJControls.model_validate(review.recommendation.applied_controls)
        return preserved_control_paths(controls) | set(plan.intent.required_paths)

    def _entering(self, review: PrepCopilotVariantApplicationResult, track_id: Any) -> TrackRecord:
        """The library track an edit would put in the list, or the edit's own refusal."""
        plan = self.backend.plan
        assert plan is not None
        # The command's snapshot already holds every library record still on disk, so
        # resolving the id against it costs no further read, and the final check reads the
        # chosen track's identity like it reads every track the proposal would list.
        library = self._sources(frozenset())
        track = next((entry[0] for entry in library.values() if _public_track(entry[0])["id"] == track_id), None)
        if track is None:
            # A track this review recorded but the disk no longer has is a changed source,
            # not an unknown one: the DJ chose it from a list that named it.
            if any(_public_track(entry[0])["id"] == track_id for entry in self.sources.values()):
                raise BackendError("stale_review", "The chosen track changed on disk; prepare a current review")
            raise BackendError("invalid_params", "Choose a library track")
        if track.path in self._paths(review):
            raise BackendError("invalid_params", "This track is already in the generated set")
        if track.metadata_status != "complete":
            raise BackendError("invalid_params", "Only a track with complete metadata can join the set")
        if track.path in plan.intent.excluded_paths:
            raise BackendError("invalid_params", "This track is excluded by the plan")
        # A track of the removed set may come back: only the plan's own exclusions keep
        # one out, and the edit that puts it back takes it out of the removed set.
        return track

    def _dropped(
        self, review: PrepCopilotVariantApplicationResult, track_id: Any
    ) -> tuple[PlaylistRecommendation, str]:
        """Take a listed track out of the list without a replacement."""
        recommendation = review.recommendation
        path = self._listed(review, track_id)
        if path in self._protected(review):
            raise BackendError("protected_track", "This track is protected by the set controls")
        if len(recommendation.ordered_tracks) - 1 < MIN_REVIEW_TRACK_COUNT:
            raise BackendError("invalid_params", f"A generated set keeps at least {MIN_REVIEW_TRACK_COUNT} tracks")
        proposed = recommendation_without_paths(
            recommendation, frozenset({path}), spectral_cohesion=self.backend.preferences.spectral_cohesion()
        )
        return proposed, path

    def _inserted(
        self, review: PrepCopilotVariantApplicationResult, track_id: Any, position: Any
    ) -> tuple[PlaylistRecommendation, TrackRecord]:
        """Put a chosen library track at a chosen position of the list."""
        recommendation = review.recommendation
        ordered = recommendation.ordered_tracks
        track = self._entering(review, track_id)
        if type(position) is not int or not 1 <= position <= len(ordered) + 1:
            raise BackendError("invalid_params", f"Insert position must be between 1 and {len(ordered) + 1}")
        if len(ordered) >= MAX_EXTENDED_TRACK_COUNT:
            raise BackendError("invalid_params", f"A generated set holds at most {MAX_EXTENDED_TRACK_COUNT} tracks")
        if position not in insertion_positions(recommendation, self._protected(review)):
            raise BackendError("protected_track", "Inserting there would break the protected controls")
        proposed = recommendation_inserted(
            recommendation, track, position, spectral_cohesion=self.backend.preferences.spectral_cohesion()
        )
        return proposed, track

    def _swapped(
        self, review: PrepCopilotVariantApplicationResult, track_id: Any, replacement_id: Any
    ) -> tuple[PlaylistRecommendation, TrackRecord, str]:
        """Replace one listed track with a chosen library track at the same position."""
        recommendation = review.recommendation
        path = self._listed(review, track_id)
        if path in self._protected(review):
            raise BackendError("protected_track", "This track is protected by the set controls")
        replacement = self._entering(review, replacement_id)
        proposed = recommendation_swapped(
            recommendation, path, replacement, spectral_cohesion=self.backend.preferences.spectral_cohesion()
        )
        return proposed, replacement, path

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

    def _extend(self, review: PrepCopilotVariantApplicationResult, target: Any) -> dict[str, Any]:
        """Grow the set toward a longer target through the best gaps in the list.

        The growth rules live in the engine (`recommendation_extended`); this
        only binds the review's own context to them -- the same candidate
        snapshot, the variant's genre filter and the library changes that make
        an edit stale -- and republishes the result like any other edit.
        """
        recommendation, plan = review.recommendation, self.backend.plan
        assert plan is not None
        current = len(recommendation.ordered_tracks)
        if type(target) is not int or not current < target <= MAX_EXTENDED_TRACK_COUNT:
            raise BackendError(
                "invalid_params",
                f"Target track count must be greater than the current list and at most {MAX_EXTENDED_TRACK_COUNT}",
            )
        current_sources = self._sources(frozenset())
        candidates = [entry[0] for path, entry in current_sources.items() if self._same(self.sources.get(path), entry)]
        in_genre, _ = _filter_tracks_for_variant(cast(PrepVariantName, review.variant_name), candidates, plan.intent)
        proposed, outside_genre = recommendation_extended(
            recommendation,
            candidates,
            target,
            spectral_cohesion=self.backend.preferences.spectral_cohesion(),
            in_genre_paths=frozenset(track.path for track in in_genre),
            locked_paths=frozenset(plan.intent.required_paths),
            excluded_paths=frozenset(plan.intent.excluded_paths) | self.removed,
            loudness_band=self.backend.preferences.loudness_band(),
        )
        added = len(proposed.ordered_tracks) - current
        if added <= 0:
            raise BackendError("no_candidates", "No eligible library track is left to extend this list")
        after = self._sources(frozenset(track.path for track in proposed.ordered_tracks), final=True)
        if any(
            not self._same(self.sources.get(track.path), after.get(track.path)) for track in proposed.ordered_tracks
        ):
            raise BackendError("stale_review", "Extension sources changed; prepare a current review")
        assessed = self._assess(proposed)
        self.verify(self.review_id)
        # A grown list is one edit: one undo step, a fresh revision, and the store rewritten.
        self._remember(self.history)
        self.future.clear()
        self._publish(
            assessed,
            self.removed,
            {
                **self.base,
                "warnings": list(
                    dict.fromkeys(
                        [
                            *rewrite_shortfall_warnings(self.base["warnings"], len(proposed.ordered_tracks)),
                            *proposed.warnings,
                        ]
                    )
                ),
            },
        )
        return {
            **self.details(),
            "extended": {"requested": target - current, "added": added, "outsideGenre": outside_genre},
        }

    def _fit_period(self, review: PrepCopilotVariantApplicationResult, year_min: Any, year_max: Any) -> dict[str, Any]:
        """Replace every track outside a release-year period that may leave, in one step.

        The replacement rules live in the engine (`recommendation_fitted`); this binds
        the review's own context to them -- the same candidate snapshot, the variant's
        genre filter and the library changes that make an edit stale -- reports what
        stayed outside and why, and republishes the result like any other edit.
        """
        recommendation, plan = review.recommendation, self.backend.plan
        assert plan is not None
        if (
            type(year_min) is not int
            or type(year_max) is not int
            or not MIN_PERIOD_YEAR <= year_min <= year_max <= MAX_PERIOD_YEAR
        ):
            raise BackendError(
                "invalid_params",
                f"A period is two years between {MIN_PERIOD_YEAR} and {MAX_PERIOD_YEAR}, the smaller first",
            )
        current_sources = self._sources(frozenset())
        candidates = [entry[0] for path, entry in current_sources.items() if self._same(self.sources.get(path), entry)]
        in_genre, _ = _filter_tracks_for_variant(cast(PrepVariantName, review.variant_name), candidates, plan.intent)
        proposed = recommendation_fitted(
            recommendation,
            candidates,
            year_min,
            year_max,
            spectral_cohesion=self.backend.preferences.spectral_cohesion(),
            in_genre_paths=frozenset(track.path for track in in_genre),
            locked_paths=frozenset(plan.intent.required_paths),
            excluded_paths=frozenset(plan.intent.excluded_paths) | self.removed,
            loudness_band=self.backend.preferences.loudness_band(),
        )
        before = [track.path for track in recommendation.ordered_tracks]
        after = [track.path for track in proposed.ordered_tracks]
        replaced = [old for old, new in zip(before, after, strict=True) if old != new]
        if not replaced:
            raise BackendError("no_candidates", "No eligible library track fits this period")
        protected = self._protected(review)
        kept = []
        for position, track in enumerate(proposed.ordered_tracks, start=1):
            year = known_release_year(track)
            if year is not None and year_min <= year <= year_max:
                continue
            kept.append(
                {
                    "position": position,
                    "title": track.title or Path(track.path).stem,
                    "year": year,
                    "reason": "protected" if track.path in protected else "no_candidate",
                }
            )
        current = self._sources(frozenset(track.path for track in proposed.ordered_tracks), final=True)
        if any(
            not self._same(self.sources.get(track.path), current.get(track.path)) for track in proposed.ordered_tracks
        ):
            raise BackendError("stale_review", "Period sources changed; prepare a current review")
        assessed = self._assess(proposed)
        self.verify(self.review_id)
        # The whole run is one edit: one undo step, a fresh revision, and the store rewritten.
        self._remember(self.history)
        self.future.clear()
        self._publish(assessed, self.removed | frozenset(replaced), dict(self.base))
        return {
            **self.details(),
            "period": {
                "yearMin": year_min,
                "yearMax": year_max,
                "replaced": len(replaced),
                "kept": kept,
            },
        }

    def execute(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if set(params) != REVIEW_FIELDS[method]:
            raise BackendError("invalid_params", "Missing or unexpected generated review fields")
            raise BackendError("invalid_params", "Missing or unexpected generated review fields")
        if method == "review.resume":
            return self.resume()
        review = self.verify(params["reviewId"])
        if method == "review.details":
            return self.details()
        if method in ("review.undo", "review.redo"):
            return self._travel(back=method == "review.undo")
        if method == "review.extend":
            return self._extend(review, params["targetTrackCount"])
        if method == "review.fit_period":
            return self._fit_period(review, params["yearMin"], params["yearMax"])
        removed = None
        entering = None
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
        elif method == "review.drop":
            proposed, removed = self._dropped(review, params["trackId"])
        elif method == "review.insert":
            proposed, entering = self._inserted(review, params["trackId"], params["position"])
        elif method == "review.swap":
            proposed, entering, removed = self._swapped(review, params["trackId"], params["replacementTrackId"])
        else:
            removed, proposed = self._replacement(review, params["trackId"])
        assessed = self._assess(proposed)
        self.verify(params["reviewId"])
        current_sources = self._sources(frozenset(track.path for track in proposed.ordered_tracks), final=True)
        if any(
            not self._same(self.sources.get(track.path), current_sources.get(track.path))
            for track in proposed.ordered_tracks
        ):
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
        # A dropped track joins the removed set; an inserted one leaves it, so a track the
        # DJ put back can be chosen again by any later edit.
        published = self.removed | {removed} if removed is not None else self.removed
        if entering is not None:
            published = published - {entering.path}
        self._publish(
            assessed,
            frozenset(published),
            {
                **self.base,
                "warnings": list(dict.fromkeys([*self.base["warnings"], *proposed.warnings])),
            },
        )
        return self.details()
