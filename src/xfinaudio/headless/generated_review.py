"""Revision-bound generated-set edits over unchanged deterministic engine helpers."""

from __future__ import annotations

import logging
from collections import Counter
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

from xfinaudio.application.prep_copilot import PrepCopilotVariantApplicationResult
from xfinaudio.exporting.explainability import PlaylistExplanation, build_playlist_explanation
from xfinaudio.headless.ai_conversation import applied_changes
from xfinaudio.headless.common import BackendError, _inside, _public_track
from xfinaudio.headless.profiles import same_recording
from xfinaudio.headless.review_evidence import evidence
from xfinaudio.headless.review_store import SAVED_FIELD, VERSION, clear_review, read_review, write_review
from xfinaudio.headless.saved_review import SAVED_VARIANT, build_saved_list
from xfinaudio.headless.serato_safety import opaque_id, source_identity
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_models import Playlist
from xfinaudio.quality.dj_readiness import DjReadinessReport, build_dj_readiness_report
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport, build_quality_report
from xfinaudio.recommendation.controls import DJControls, preserved_control_paths
from xfinaudio.recommendation.playlist_service import (
    PlaylistRecommendation,
    in_plan_period,
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
# The sources, the policy, and the paths that were already unusable when the plan
# was captured: those stay out of the plan but do not invalidate its own binding.
PlanBinding = tuple[SourceSnapshot, tuple[object, ...], frozenset[str]]

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
TAG_WRITE_ACCEPTED = "A tag rewrite kept the same recording; the review source identity was refreshed"
# The library derives these from the audio itself: a later analysis pass rewrites them
# without the file, its tags or the recording identity the scan bound changing (S1).
ANALYSIS_PROFILE_FIELDS = (
    "spectral_profile",
    "danceability_profile",
    "edge_spectral_profile",
    "loudness_profile",
    "tonal_profile",
)
ReviewState = tuple[PrepCopilotVariantApplicationResult, frozenset[str], dict[str, Any]]


def _same_listed_track(recorded: TrackRecord, current: TrackRecord) -> bool:
    """Whether both records describe the same track, ignoring derived analysis data (S1).

    A later analysis pass rewrites only the spectral, danceability, edge, loudness and
    tonal profiles; the file, its tags and the recording the library scanned stay the same.
    """
    derived: dict[str, Any] = dict.fromkeys(ANALYSIS_PROFILE_FIELDS)
    return recorded.model_copy(update=derived) == current.model_copy(update=derived)


def _root_accessible(root: Path) -> bool:
    """Whether one authorized library root is readable now, as a real directory.

    An external drive that is not mounted, or a root the user moved away, is not: that
    says nothing about the files a stored list holds (S2).
    """
    try:
        return root.is_dir() and not root.is_symlink() and root.resolve(strict=True) == root
    except (OSError, RuntimeError):
        return False


def _renewed(recommendation: PlaylistRecommendation, records: dict[str, TrackRecord]) -> PlaylistRecommendation:
    """The recommendation carrying the library's current record of every track it lists (S1)."""
    tracks = [records.get(track.path, track) for track in recommendation.ordered_tracks]
    if tracks == recommendation.ordered_tracks:
        return recommendation
    return recommendation.model_copy(update={"ordered_tracks": tracks})


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
        # The playlist a saved list was opened from, as it was when this review bound it:
        # only ``playlist.save_review`` writes back, and only while it still matches.
        self.saved_playlist: Playlist | None = None
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
        # Paths accepted as the same recording after an external tag write (S20).
        self._rewritten: set[str] = set()

    def _policy(self) -> tuple[object, ...]:
        return self.backend.preferences.spectral_cohesion(), self.backend.preferences.loudness_band()

    @property
    def in_command(self) -> bool:
        """Whether one core command is running, so its guards share one library read (S3)."""
        return bool(self._scope_depth)

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
                # The library rows one command read are not kept past it, so nothing stale
                # and no second copy of a large library outlives the command (S3).
                self.backend._forget_library_rows()

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

    def _build_sources(
        self, checked: frozenset[str] | None, *, unread: bool = False, listed_only: bool = False
    ) -> SourceSnapshot:
        """Read the library sources exactly as they are now, for the ``checked`` paths.

        Every library track is checked on disk, and the ``checked`` paths are the ones the
        caller acts on: every other track contributes its stored record and the identity
        the generation recorded, so a review command never re-reads a track it does not
        act on. The result belongs to the caller: one command copies the entries it asked
        for into its own snapshot.

        ``listed_only`` is the assistant context's own mode (S3): a track outside
        ``checked`` then keeps its stored record and identity behind a single lexical root
        test instead of an existence check, so one prepared turn resolves tens of paths
        and not every library file. Every other caller keeps the existence check, so a
        deleted library track still leaves the snapshot -- and the candidate pools built
        from it -- exactly as it always did.

        ``unread`` keeps every unlisted library track even before this review recorded
        anything about it, with its stored record and no identity: that is the whole
        library a restart restores, without reading the disk of the tracks it does not
        list. A checked path whose file identity changed into a different recording, an
        unreadable file or a replacement leaves the snapshot entirely (S5).
        """
        result = {}
        tracks = self.backend._records(checked=checked)
        read_paths = [track.path for track in tracks if checked is None or track.path in checked]
        stored_identities = self.backend.repository.load_scan_file_identities(read_paths)
        for track in tracks:
            path = Path(track.path)
            if listed_only and checked is not None and track.path not in checked:
                # Decided before anything touches the disk: this turn never acts on the
                # track, and a lexical test is all that decides whether it still belongs to
                # an authorized root (S3).
                if not any(path.is_relative_to(root) for root in self.backend.roots):
                    continue
                stored = self.sources.get(track.path)
                if stored is not None:
                    result[track.path] = track, stored[1]
                elif unread:
                    result[track.path] = track, None
                continue
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
                identity = source_identity(path)
                recorded = stored_identities.get(track.path)
                if (
                    recorded is not None
                    and None not in recorded
                    and (recorded[0], recorded[1]) != (identity[4], identity[3])
                    and not same_recording(track, path)
                ):
                    continue
                entry: SourceEntry = (track, identity)
                if self.backend.review is not None:
                    healed = self._recording_entry(track, identity, path)
                    if healed is not None:
                        entry = healed
                result[track.path] = entry
            except (OSError, RuntimeError):
                pass
        return result

    def _recording_entry(self, track: TrackRecord, identity: tuple[object, ...], path: Path) -> SourceEntry | None:
        """Keep the recorded entry when a tag write changed only the file identity.

        The library's own audio reader confirms the file is still readable audio of the
        same duration at the same path, so the review keeps the metadata it recorded and
        refreshes that identity. A file that fails the check keeps behaving as before.
        """
        recorded = self.sources.get(track.path)
        if recorded is None or recorded[1] is None:
            return None
        if recorded[1] != identity:
            if not same_recording(recorded[0], path):
                return None
            self.sources[track.path] = (recorded[0], identity)
            self._rewritten.add(track.path)
            LOGGER.info(TAG_WRITE_ACCEPTED)
            return (recorded[0], identity)
        # The library still records the older identity, so its freshly read record has
        # lost the profiles this review recorded; the accepted file keeps that record.
        if track.path in self._rewritten:
            return (recorded[0], identity)
        return None

    def _tag_written(self, path: str, identity: tuple[object, ...]) -> bool:
        """Whether the library recorded a different identity for this exact path."""
        recorded = self.backend.repository.load_scan_file_identities([path]).get(path)
        return (
            recorded is not None and None not in recorded and (recorded[0], recorded[1]) != (identity[4], identity[3])
        )

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

    def _unchanged(self, binding: PlanBinding, current: SourceSnapshot, checked: frozenset[str] | None = None) -> bool:
        """Whether every recorded track is still what it was, and no track left the library.

        ``checked`` names the tracks the command acts on: only those decide, so a library
        track that is in no variant may change without invalidating the plan (S15). A
        tag-only rewrite changes just the file identity: the plan binding accepts it
        with the refreshed identity, as S20 accepts it for a review (S5). A path that
        was already unusable at capture time stays outside both sides of the check; a
        source that changed afterwards is still a change.
        """
        recorded, _, excluded = binding
        if checked is not None:
            return all(self._binding_same(recorded.get(path), current.get(path)) for path in checked)
        return set(recorded) | excluded == set(current) | excluded and all(
            self._binding_same(recorded[path], current.get(path)) for path in recorded
        )

    def _binding_same(self, recorded: SourceEntry | None, current: SourceEntry | None) -> bool:
        if recorded is None or current is None:
            return False
        if recorded[0] != current[0]:
            return False
        if recorded[1] is None or recorded[1] == current[1]:
            return True
        return current[1] is not None and same_recording(recorded[0], Path(recorded[0].path))

    def _reverify(self, recorded: SourceSnapshot, checked: frozenset[str] | None = None) -> SourceSnapshot:
        """Re-read a snapshot the way it was recorded: only where it recorded an identity.

        A generation snapshot covers the whole library, so its verification reads the whole
        library, and a track that appeared since is still a change. A restart records
        identities only for the tracks its list holds, so its verification reads those and
        keeps every other library track with the record the scan stored. ``checked`` names
        the tracks the command acts on -- the tracks of the plan's variants -- so a
        generation neither reads nor refuses anything over the rest of the library (S15).
        """
        read = frozenset(path for path, entry in recorded.items() if entry[1] is not None)
        if checked is not None:
            read &= checked
        return self._reread(read)

    def _reread(self, paths: frozenset[str]) -> SourceSnapshot:
        """Read these identities from disk now, whatever the command already read (S15).

        A plan guard must notice a file that changed after the command started, so unlike
        the guards that reuse what the command already read, this one always reads the disk.
        Inside a command it fills that command's snapshot path by path, so nothing else in
        the command pays for those tracks again; outside one it is a plain read of them.
        """
        if not self._scope_depth:
            return self._build_sources(paths, unread=True)
        if self._snapshot is None:
            self._snapshot = self._build_sources(paths, unread=True)
            self._fresh = set(paths)
            return self._snapshot
        current = self._build_sources(paths)
        for path in paths:
            if path in current:
                self._snapshot[path] = current[path]
            else:
                # A moved, deleted or unreadable source is absent, never trusted.
                self._snapshot.pop(path, None)
        if self._fresh is not None:
            self._fresh |= paths
        return self._snapshot

    def capture_plan(self, records: list[TrackRecord]) -> PlanBinding:
        """Capture the inputs before the engine runs, never on later selection."""
        sources = self._sources()
        if any(sources[track.path][0] != track for track in records if track.path in sources):
            raise BackendError("stale_plan", "Library metadata changed before preparation; regenerate")
        # This generation owns its snapshot from now on: an earlier review's recorded
        # metadata must not heal the plan's own sources when the plan is bound.
        self.sources = dict(sources)
        self._rewritten.clear()
        excluded = frozenset(track.path for track in records if track.path not in sources)
        # The binding is captured as it is: the command's snapshot keeps being filled with
        # the identities its guards read, and that must never rewrite what was captured.
        return dict(sources), self._policy(), excluded

    def bind_plan(self, plan_id: str, binding: PlanBinding, checked: frozenset[str] | None = None) -> None:
        """Publish only a plan whose complete candidate context is still current.

        ``checked`` names the tracks the plan's variants list, so the publication reads and
        compares those and not the whole library (S15).
        """
        if not self._unchanged(binding, self._reverify(binding[0], checked), checked) or self._policy() != binding[1]:
            raise BackendError("stale_plan", "Library sources or settings changed during preparation; regenerate")
        self.plan_id, self.plan_binding = plan_id, binding

    def verify_plan(self, plan_id: str, checked: frozenset[str] | None = None) -> None:
        """Refuse a plan whose own tracks or settings changed, reading only ``checked``."""
        binding = self.plan_binding
        if (
            self.plan_id != plan_id
            or binding is None
            or not self._unchanged(binding, self._reverify(binding[0], checked), checked)
            or self._policy() != binding[1]
        ):
            raise BackendError("stale_plan", "The generation context changed; generate a current plan")

    def bind(
        self,
        snapshot: dict[str, Any],
        *,
        saved: Playlist | None = None,
        checked: frozenset[str] | None = None,
    ) -> dict[str, Any]:
        """Bind immediately after selecting a generated variant, before publication.

        ``saved`` is the playlist an opened saved list stays tied to (S3), and unlike a
        generated one it is stored with the review, so the list comes back after a restart.
        ``checked`` is the variant this command chose: the final check reads those tracks
        and nothing else (S15).
        """
        self.review_id = self.backend.review_id
        self.base = dict(snapshot)
        assert self.backend.plan_id is not None
        try:
            self.verify_plan(self.backend.plan_id, checked)
        except BackendError:
            self.backend._clear_review()
            self.review_id = None
            raise
        assert self.plan_binding is not None
        recorded, policy, _ = self.plan_binding
        self.sources, self.policy = dict(recorded), policy
        # A generated list is never written back to a playlist it was not opened from.
        self.saved_playlist = saved
        self.removed = frozenset()
        self._rewritten.clear()
        # The final check just read these tracks: the review records the identities it
        # confirmed, and a file a tag write changed only in identity keeps the metadata
        # this review recorded for it, exactly as the healing read of an edit would (S20).
        for path in checked or frozenset():
            confirmed = (self._snapshot or {}).get(path)
            before = recorded.get(path)
            if confirmed is None or before is None:
                continue
            if before[1] is not None and before[1] != confirmed[1]:
                self._rewritten.add(path)
            self.sources[path] = confirmed
        self.history.clear()
        self.future.clear()
        self.offers.clear()
        self._persist()
        return self.details()

    def bind_saved(self, playlist: Playlist, tracks: list[TrackRecord]) -> dict[str, Any]:
        """Open a saved playlist as the list in progress: the review a generation binds (S3).

        The engine scores the saved order and the list is bound to a synthetic plan
        with no controls, so the first and the last track stay editable. The list owns
        its own source snapshot: only the tracks it holds are read from disk.
        """
        saved = build_saved_list(playlist.name, tracks)
        # Opening another list discards the one in progress, including its stored copy.
        self.backend.invalidate_review()
        self.saved_playlist = None
        self.sources = {}
        plan_id, review_id = str(uuid4()), str(uuid4())
        self.backend.plan, self.backend.plan_id = saved.plan, plan_id
        self.backend.review, self.backend.review_id = saved.review, review_id
        self.backend.review_blocked = bool(saved.blockers) or not saved.review.recommendation.ordered_tracks
        binding: PlanBinding = (
            self._build_sources(self._paths(saved.review), unread=True),
            self._policy(),
            frozenset(),
        )
        self.bind_plan(plan_id, binding)
        review = saved.review
        result = self.bind(
            {
                "planId": plan_id,
                "variants": [saved.variant_summary()],
                "reviewId": review_id,
                "name": playlist.name,
                "variant": SAVED_VARIANT,
                "savedPlaylistId": playlist.id,
                "editable": True,
                "tracks": [_public_track(track) for track in review.recommendation.ordered_tracks],
                "warnings": list(review.recommendation.warnings),
                "blockers": saved.blockers,
                "qualityScore": review.quality_report.average_transition_score,
                "readiness": review.readiness_report.status,
            },
            saved=playlist,
        )
        return result

    def save_review(self, review_id: Any) -> dict[str, Any]:
        """Write the list in progress back to the playlist it was opened from (S3, S6).

        The order goes to the same playlist through the compare-and-update every save
        uses, so a playlist renamed or saved elsewhere meanwhile is refused with
        ``stale_edit``. The review keeps its identity: nothing about the list changed,
        only the saved version it is compared against -- and the stored copy follows, so a
        restart before the next edit still saves into the playlist it just wrote.
        """
        review = self.verify(review_id)
        playlist = self.saved_playlist
        if playlist is None:
            raise BackendError("stale_review", "Open a saved playlist before saving its order back")
        paths = [track.path for track in review.recommendation.ordered_tracks]
        saved = self.backend.playlists.compare_and_update(playlist, name=playlist.name, track_paths=paths)
        if saved is None:
            raise BackendError("stale_edit", "The saved playlist changed; open it again before saving")
        self.saved_playlist = saved
        self._persist()
        return {"id": saved.id, "name": saved.name, "trackCount": len(saved.track_paths)}

    @staticmethod
    def _paths(review: PrepCopilotVariantApplicationResult) -> frozenset[str]:
        """The tracks this review's list holds: the ones every edit acts on."""
        return frozenset(track.path for track in review.recommendation.ordered_tracks)

    def verify(self, review_id: Any, *, listed_only: bool = False) -> PrepCopilotVariantApplicationResult:
        """Verify this review, checking every library track on disk unless ``listed_only``.

        ``listed_only`` is the assistant context's own mode (S3): the tracks outside the
        list keep their stored record and identity, so one prepared turn never walks the
        whole library on disk. It builds its own snapshot instead of filling the command's,
        so a review edit made later in the same command still sees every library file.
        """
        opaque_id(review_id)
        review = self.backend.review
        if review is None or review_id != self.backend.review_id or review_id != self.review_id:
            raise BackendError("stale_review", "Open a current generated review before continuing")
        paths = self._paths(review)
        current = self._build_sources(paths, listed_only=True) if listed_only else self._sources(paths)
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
        """Rebind the review a previous process stored, or drop it honestly.

        A saved list comes back exactly like a generated one, and with the playlist it
        was opened from (S3): the stored version is the one the next save is compared
        against, so a playlist deleted or changed meanwhile still restores the list but
        refuses to write it back.
        """
        payload = read_review(self.backend.data_dir)
        if payload is None:
            return
        try:
            review = self._decode(payload["review"])
            plan = PrepCopilotPlan.model_validate(payload["plan"])
            if payload["variant"] != review.variant_name:
                raise ValueError("Stored variant does not describe the stored review")
            stored_playlist = payload.get(SAVED_FIELD)
            saved_playlist = None if stored_playlist is None else self._playlist(stored_playlist)
        except (KeyError, TypeError, ValueError):
            LOGGER.warning("The stored list in progress could not be decoded; it is dropped")
            clear_review(self.backend.data_dir)
            return
        sources = self._build_sources(self._paths(review), unread=True)
        # An external tag write changes only the file identity: the reader it invalidated
        # drops the recorded profiles from the freshly read record. When the library's own
        # audio reader confirms the same recording at the same path, the stored list keeps
        # its metadata and binds to the identity the file has now (S20).
        self._rewritten.clear()
        for track in review.recommendation.ordered_tracks:
            current = sources.get(track.path)
            if current is None or current[1] is None:
                continue
            if self._tag_written(track.path, current[1]) and same_recording(track, Path(track.path)):
                sources[track.path] = (track, current[1])
                self._rewritten.add(track.path)
                LOGGER.info(TAG_WRITE_ACCEPTED)
        listed = review.recommendation.ordered_tracks
        # A listed track the library can read now but no longer describes as the track it
        # recorded is a real library change.
        changed = [
            track for track in listed if track.path in sources and not _same_listed_track(track, sources[track.path][0])
        ]
        unverified = [track for track in listed if track.path not in sources]
        # A listed path the library cannot read is a file that left the library for good
        # while its root is still there; only a root the core cannot read -- a drive that
        # is not mounted yet -- leaves the file unverified and the list stored (S2).
        removed = [track for track in unverified if self._root_ready(track.path)]
        if changed or removed:
            LOGGER.warning("The list in progress was dropped because the library changed")
            clear_review(self.backend.data_dir)
            self.dropped = True
            return
        if unverified:
            # The stored copy is never deleted because this start could not verify a
            # track: the next start, with the drive mounted, still recovers the list (S2).
            LOGGER.warning(
                "The list in progress could not be verified because its drive is not reachable (%s); it is kept",
                unverified[0].path,
            )
            self.dropped = True
            return
        # A later analysis pass rewrites only derived profile data, and the list comes
        # back over the library's current records, which every later edit compares (S1).
        renewed = {path: entry[0] for path, entry in sources.items()}
        if any(track != renewed[track.path] for track in listed):
            review = replace(review, recommendation=_renewed(review.recommendation, renewed))
            plan = plan.model_copy(
                update={
                    "variants": [
                        variant.model_copy(update={"recommendation": _renewed(variant.recommendation, renewed)})
                        for variant in plan.variants
                    ]
                }
            )
        self.backend.plan, self.backend.plan_id = plan, payload["planId"]
        self.sources, self.policy = sources, self._policy()
        self.saved_playlist = saved_playlist
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
        if saved_playlist is not None:
            # A restored saved list answers the payload it was opened with (S3).
            self.base["savedPlaylistId"] = saved_playlist.id
            self.base["editable"] = True
        self.history.clear()
        self.future.clear()
        self.offers.clear()
        # Bind against the library as it is now, so every later edit keeps the stale-source
        # checks. The binding re-reads the tracks the list holds and no other one, so a
        # change made while restoring is still refused.
        self.bind_plan(payload["planId"], (self.sources, self.policy, frozenset()))

    def _root_ready(self, path: str) -> bool:
        """Whether the authorized roots that hold this path are readable now (S2).

        A listed file missing under a root the core can read was removed from the library
        for good. A root that is not there is a drive that is not mounted yet, which says
        nothing about the file. A path no configured root holds any more belongs to no
        library this start could ever restore, so it is treated as removed too.
        """
        target = Path(path)
        return all(_root_accessible(root) for root in self.backend.roots if target.is_relative_to(root))

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
        payload: dict[str, Any] = {
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
        if self.saved_playlist is not None:
            # A saved list stays tied to its playlist across a restart (S3).
            payload[SAVED_FIELD] = self._saved(stored=self.saved_playlist)
        return payload

    @staticmethod
    def _saved(*, stored: Playlist) -> dict[str, Any]:
        """Store the playlist exactly as this review last saw it, never a later state."""
        assert stored.id is not None
        return {
            "id": stored.id,
            "name": stored.name,
            "createdAt": stored.created_at.isoformat(),
            "updatedAt": stored.updated_at.isoformat(),
            "trackPaths": list(stored.track_paths),
        }

    @staticmethod
    def _playlist(stored: dict[str, Any]) -> Playlist:
        """Rebuild the playlist snapshot a stored review is compared against."""
        return Playlist(
            id=stored["id"],
            name=stored["name"],
            created_at=datetime.fromisoformat(stored["createdAt"]),
            updated_at=datetime.fromisoformat(stored["updatedAt"]),
            track_paths=list(stored["trackPaths"]),
        )

    def _persist(self) -> None:
        """Store the review after every change; a refused write never fails the edit it follows."""
        try:
            write_review(self.backend.data_dir, self._payload())
        except (OSError, TypeError, ValueError):
            LOGGER.warning("The list in progress could not be stored; the change stays in memory")

    def clear_stored(self) -> None:
        """Forget the stored review when the backend discards the active one."""
        clear_review(self.backend.data_dir)
        # A discarded list no longer writes back to the playlist it was opened from.
        self.saved_playlist = None
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

    def _candidate_pool(self) -> list[TrackRecord]:
        """The library tracks an engine edit may pick from, period included (S17).

        A plan generated with a release period keeps it: growth, and the replacement an
        edit offers, only consider tracks whose year is inside that period. An explicit
        choice -- ``review.insert`` and ``review.swap`` -- never comes through here, so
        the DJ can still name any library track. A plan without a period keeps every
        track, exactly as before.
        """
        plan = self.backend.plan
        assert plan is not None
        current = self._sources(frozenset())
        candidates = [entry[0] for path, entry in current.items() if self._same(self.sources.get(path), entry)]
        return [track for track in candidates if in_plan_period(track, plan.intent.year_min, plan.intent.year_max)]

    def _replacement(
        self, review: PrepCopilotVariantApplicationResult, track_id: Any
    ) -> tuple[str, PlaylistRecommendation]:
        recommendation, plan = review.recommendation, self.backend.plan
        assert plan is not None
        target = self._listed(review, track_id)
        if target in self._protected(review):
            raise BackendError("protected_track", "This track is protected by the set controls")
        candidates = self._candidate_pool()
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
        # S17: the outside-genre pool the engine may bridge into is period-scoped too, so a
        # list generated with a period never grows past the tracks that period holds.
        candidates = [
            track for track in candidates if in_plan_period(track, plan.intent.year_min, plan.intent.year_max)
        ]
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
            # A track's id comes from its path, so a repeated track shares one id:
            # the order must name each id exactly as many times as the list holds it.
            tracks = {_public_track(track)["id"]: track for track in review.recommendation.ordered_tracks}
            current_ids = [_public_track(track)["id"] for track in review.recommendation.ordered_tracks]
            if (
                not isinstance(ids, list)
                or any(not isinstance(item, str) for item in ids)
                or Counter(ids) != Counter(current_ids)
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
