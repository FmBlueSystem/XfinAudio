"""Local application commands with opaque public track identities and read-only scans."""

from __future__ import annotations

import json
import stat
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID, uuid4

from xfinaudio.application.playlist_workflow import PlaylistWorkflowService
from xfinaudio.application.prep_copilot import (
    PrepCopilotVariantApplicationResult,
    PrepCopilotVariantLike,
    build_prep_copilot_variant_application,
)
from xfinaudio.application.saved_playlists import SavedPlaylistService
from xfinaudio.headless.ai_protocol import AI_FIELDS
from xfinaudio.headless.common import BackendError, _inside, _public_track, _text
from xfinaudio.headless.generated_review import REVIEW_FIELDS, GeneratedReview
from xfinaudio.headless.legacy_import import LEGACY_FIELDS, LegacyImport, recover_legacy_import
from xfinaudio.headless.library_browse import BROWSE_FIELDS, LibraryBrowser
from xfinaudio.headless.live_session import LIVE_FIELDS, LiveGuidance
from xfinaudio.headless.loudness import LOUDNESS_FIELDS, LoudnessWorkflow
from xfinaudio.headless.metadata_report import build_metadata_report
from xfinaudio.headless.playlist_editor import EDIT_FIELDS, PlaylistEditor
from xfinaudio.headless.preferences import SETTINGS_FIELDS, PreferencesService
from xfinaudio.headless.prep import GENERATE_FIELDS, VARIANT_NAMES, catalog, generate_plan, make_intent
from xfinaudio.headless.prep_settings import PREP_SETTINGS_FIELDS, PrepSettings
from xfinaudio.headless.profiles import PROFILE_FIELDS, ProfileCompletion, current_records
from xfinaudio.headless.saved_browser import SAVED_FIELDS, SavedBrowser
from xfinaudio.headless.serato_export import SERATO_FIELDS, SeratoExporter
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_repository import PlaylistRepository
from xfinaudio.library.scan_planning import SUPPORTED_AUDIO_EXTENSIONS
from xfinaudio.library.scan_service import (
    MetadataScanService,
    ProfileCache,
    ProgressCallback,
    ScanCancellationToken,
    ScanProgress,
    read_mutagen_tags,
)
from xfinaudio.library.track_repository import TrackRepository
from xfinaudio.recommendation.prep_copilot import PrepCopilotPlan

if TYPE_CHECKING:
    from xfinaudio.headless.optional_ai import OptionalAI

Progress = Callable[[dict[str, Any]], None]
MIME_TYPES = {
    ".flac": "audio/flac",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".wav": "audio/wav",
    ".aif": "audio/aiff",
    ".aiff": "audio/aiff",
}


class ConfinedScanService:
    """Adapt the existing metadata scanner, excluding symlinks and external paths."""

    def scan(
        self,
        folder: Path,
        *,
        on_progress: ProgressCallback | None = None,
        cancellation_token: ScanCancellationToken | None = None,
        parallel_spectral_analysis: bool = True,
        spectral_max_workers: int | None = None,
        previous_profile_cache: ProfileCache | None = None,
        profile_cache_loader: Callable[[list[Path]], ProfileCache] | None = None,
        resolve_spectral_profiles: bool = True,
    ) -> list[TrackRecord]:
        def paths(root: Path):
            for path in root.rglob("*"):
                if cancellation_token is not None and cancellation_token.is_cancelled:
                    break
                if path.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS and _inside(path, root) and path.is_file():
                    yield path

        def tags(path: Path) -> dict[str, Any] | None:
            return read_mutagen_tags(path) if _inside(path, folder) else None

        return MetadataScanService().scan(
            folder,
            list_paths=paths,
            read_tags=tags,
            on_progress=on_progress,
            cancellation_token=cancellation_token,
            resolve_spectral_profiles=False,
            parallel_spectral_analysis=False,
            profile_cache_loader=profile_cache_loader,
        )


class HeadlessBackend:
    """Own isolated repositories; use domain services without desktop or provider imports."""

    def __init__(self, data_dir: Path | str) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        recover_legacy_import(self.data_dir)
        self.repository = TrackRepository(self.data_dir / "tracks.db")
        self.playlists = PlaylistRepository(self.data_dir / "playlists.db")
        self.saved = SavedPlaylistService(repository=self.playlists)
        self.workflow = PlaylistWorkflowService(scan_service=ConfinedScanService(), repository=self.repository)
        self.roots: list[Path] = []
        roots_file = self.data_dir / "roots.json"
        if roots_file.exists():
            try:
                stored = json.loads(roots_file.read_text(encoding="utf-8"))
                if isinstance(stored, list) and all(isinstance(p, str) and Path(p).is_absolute() for p in stored):
                    self.roots = [Path(p) for p in stored]
            except (OSError, ValueError):
                pass  # Corrupt authorization state fails closed until another explicit scan.
        self.plan: PrepCopilotPlan | None = None
        self.plan_id: str | None = None
        self.review: PrepCopilotVariantApplicationResult | None = None
        self.review_id: str | None = None
        self.review_blocked = True
        self._track_paths: dict[str, str] = {}
        self._records()
        self.editor = PlaylistEditor(self)
        self.browse = LibraryBrowser(self)
        self.saved_browser = SavedBrowser(self)
        self.serato = SeratoExporter(self)
        self.live = LiveGuidance(self)
        self.preferences = PreferencesService(self)
        self.loudness = LoudnessWorkflow(self)
        self.profiles = ProfileCompletion(self)
        self.review_actions = GeneratedReview(self)
        self.prep_settings = PrepSettings(self)
        self.legacy_import = LegacyImport(self)
        self._optional_ai: OptionalAI | None = None

    @property
    def optional_ai(self) -> OptionalAI:
        """Compose language adapters only when optional assistance is requested."""
        if self._optional_ai is None:
            from xfinaudio.headless.optional_ai import OptionalAI

            self._optional_ai = OptionalAI(self)
        return self._optional_ai

    def invalidate_optional_ai(self) -> None:
        """Baseline local workflows must not load a never-used provider facade."""
        if self._optional_ai is not None:
            self._optional_ai.invalidate()

    def shutdown(self) -> None:
        """Drain already-created loudness resources without probing or starting an engine."""
        self.loudness.shutdown()

    def invalidate_review(self) -> None:
        """Discard any completed or in-flight review identity after cancellation or new work."""
        self.plan = None
        self.plan_id = None
        self._clear_review()

    def _clear_review(self) -> None:
        self.review = None
        self.review_id = None
        self.review_blocked = True

    def _records(self) -> list[TrackRecord]:
        records = [
            record
            for record in self.repository.list_display_tracks()
            if any(Path(record.path).is_relative_to(root) for root in self.roots)
        ]
        records = current_records(self.repository, records, self.roots)
        # Publish a new snapshot; never mutate the mapping read by concurrent previews.
        self._track_paths = {str(_public_track(record)["id"]): record.path for record in records}
        return records

    def _library(self) -> dict[str, Any]:
        records = self._records()
        complete = sum(track.metadata_status == "complete" for track in records)
        return {
            "tracks": [_public_track(track) for track in records],
            "completeCount": complete,
            "incompleteCount": len(records) - complete,
        }

    def execute(
        self,
        method: str,
        params: dict[str, Any],
        *,
        cancellation_token: ScanCancellationToken | None = None,
        progress: Progress | None = None,
    ) -> dict[str, Any]:
        if self.legacy_import.restart_required:
            raise BackendError("legacy_restart_required", "Restart before using imported data")
        allowed = {
            "library.scan": {"root"},
            "library.roots": set(),
            "library.rescan": set(),
            "library.list": set(),
            "metadata.report": set(),
            "prep.catalog": set(),
            "prep.generate": GENERATE_FIELDS,
            "prep.select": {"planId", "variant"},
            "playlist.save": {"name", "reviewId"},
            "playlist.list": set(),
            "playlist.open": {"playlistId"},
            "track.resolve": {"trackId"},
            **EDIT_FIELDS,
            **SERATO_FIELDS,
            **LIVE_FIELDS,
            **SETTINGS_FIELDS,
            **LOUDNESS_FIELDS,
            **AI_FIELDS,
            **PROFILE_FIELDS,
            **BROWSE_FIELDS,
            **SAVED_FIELDS,
            **REVIEW_FIELDS,
            **PREP_SETTINGS_FIELDS,
            **LEGACY_FIELDS,
        }
        if method not in allowed:
            raise BackendError("unknown_method", "Unknown command")
        if method in ("library.scan", "library.rescan"):
            self.editor.invalidate()
            self.profiles.invalidate()
            self.loudness.invalidate()
            self.invalidate_optional_ai()
        if method in ("library.scan", "library.rescan", "prep.generate"):
            self.invalidate_review()
        elif method == "prep.select":
            self._clear_review()
        if not isinstance(params, dict) or set(params) - allowed[method]:
            raise BackendError("invalid_params", "Unexpected command parameters")
        if method in LEGACY_FIELDS:
            return self.legacy_import.execute(method, params)
        if method in REVIEW_FIELDS:
            return self.review_actions.execute(method, params)
        if method in PREP_SETTINGS_FIELDS:
            return self.prep_settings.execute(method, params)
        if method in BROWSE_FIELDS:
            return self.browse.execute(method, params)
        if method in SAVED_FIELDS:
            return self.saved_browser.execute(method, params)
        if method in PROFILE_FIELDS:
            return self.profiles.execute(
                method, params, cancellation_token or ScanCancellationToken(), progress or (lambda data: None)
            )
        if method in AI_FIELDS:
            return self.optional_ai.execute(
                method, params, cancellation_token or ScanCancellationToken(), progress or (lambda data: None)
            )
        if method in LOUDNESS_FIELDS:
            if method == "loudness.run":
                self.invalidate_optional_ai()
            return self.loudness.execute(
                method, params, cancellation_token or ScanCancellationToken(), progress or (lambda data: None)
            )
        if method in SETTINGS_FIELDS:
            return self.preferences.execute(method, params)
        if method in LIVE_FIELDS:
            return self.live.execute(method, params)
        if method in SERATO_FIELDS:
            return self.serato.execute(method, params)
        if method in EDIT_FIELDS:
            return self.editor.execute(method, params)
        token = cancellation_token or ScanCancellationToken()
        emit = progress or (lambda data: None)
        if method == "library.roots":
            return {"roots": [str(root) for root in self.roots]}
        if method == "library.rescan":
            return self._rescan(token, emit)
        if method == "library.scan":
            return self._scan(params, token, emit)
        if method == "library.list":
            return self._library()
        if method == "metadata.report":
            return build_metadata_report(self._records(), locked_paths=frozenset())
        if method == "prep.catalog":
            return catalog()
        if method == "prep.generate":
            return self._generate(params, token, emit)
        if method == "prep.select":
            return self._select(params, token)
        if method == "playlist.save":
            name = _text(params.get("name"), "playlist name")
            review_id = _text(params.get("reviewId"), "review identity")
            if self.review is None or review_id != self.review_id:
                raise BackendError("stale_review", "Generate and review a current playlist before saving")
            self.review_actions.verify(review_id)
            if self.review_blocked:
                raise BackendError("blocked_review", "Resolve the review blockers before saving")
            playlist = self.saved.save_recommendation(self.review.recommendation, name=name)
            return {
                "id": playlist.id,
                "name": playlist.name,
                "trackCount": len(playlist.track_paths),
                "updatedAt": playlist.updated_at.isoformat(),
            }
        if method == "playlist.list":
            return {
                "playlists": [
                    {
                        "id": item.id,
                        "name": item.name,
                        "trackCount": item.track_count,
                        "updatedAt": item.updated_at.isoformat(),
                    }
                    for item in self.playlists.list_summaries()
                ]
            }
        if method == "playlist.open":
            playlist_id = params.get("playlistId")
            if type(playlist_id) is not int or playlist_id <= 0:
                raise BackendError("invalid_params", "Invalid playlist identity")
            playlist = self.playlists.get_by_id(playlist_id)
            if playlist is None:
                raise BackendError("not_found", "Playlist was not found")
            records = {track.path: track for track in self._records()}
            tracks = [
                records[path]
                for path in playlist.track_paths
                if path in records and any(_inside(Path(path), root) for root in self.roots) and Path(path).is_file()
            ]
            return {
                "id": playlist.id,
                "name": playlist.name,
                "tracks": [_public_track(track) for track in tracks],
                "missingTrackCount": len(playlist.track_paths) - len(tracks),
            }
        track_id = _text(params.get("trackId"), "track identity", 64)
        path_text = self._track_paths.get(track_id)
        if path_text is None:
            raise BackendError("not_found", "Track was not found in an authorized library")
        path = Path(path_text)
        try:
            before = path.lstat()
            if not stat.S_ISREG(before.st_mode) or not any(_inside(path, root) for root in self.roots):
                raise OSError("Unconfined preview")
            after = path.lstat()
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
            ):
                raise OSError("Changed preview")
        except (OSError, RuntimeError) as exc:
            raise BackendError("not_found", "Track is missing or outside the authorized library") from exc
        mime = MIME_TYPES.get(path.suffix.lower())
        if mime is None:
            raise BackendError("invalid_track", "Unsupported preview format")
        return {
            "path": str(path),
            "mime": mime,
            "identity": {
                "device": str(after.st_dev),
                "inode": str(after.st_ino),
                "size": str(after.st_size),
                "mtimeNs": str(after.st_mtime_ns),
            },
        }

    def _rescan(self, token: ScanCancellationToken, emit: Progress) -> dict[str, Any]:
        if not self.roots:
            raise BackendError("not_found", "Choose a library folder before rescanning")
        roots = tuple(self.roots)
        try:
            if any(not root.is_dir() or root.is_symlink() or root.resolve(strict=True) != root for root in roots):
                raise OSError("A registered folder changed or is unavailable")
        except (OSError, RuntimeError) as error:
            raise BackendError("library_unavailable", "A registered folder is unavailable; choose it again") from error
        for root in roots:
            if token.is_cancelled:
                break
            result = self._scan({"root": str(root)}, token, emit)
            if result["cancelled"]:
                break
        return {**self._library(), "cancelled": token.is_cancelled}

    def _scan(self, params: dict[str, Any], token: ScanCancellationToken, emit: Progress) -> dict[str, Any]:
        _text(params.get("root"), "folder", 4096)
        root = Path(params["root"])
        if not root.is_absolute() or not root.is_dir() or root.is_symlink():
            raise BackendError("invalid_params", "Choose an existing absolute library folder")
        root = root.resolve(strict=True)
        self.invalidate_review()
        if root not in self.roots:
            self.roots.append(root)
            pending = self.data_dir / "roots.json.tmp"
            pending.write_text(json.dumps([str(path) for path in self.roots]), encoding="utf-8")
            pending.replace(self.data_dir / "roots.json")

        def progress(update: ScanProgress) -> None:
            emit(
                {
                    "phase": "scan",
                    "processedCount": update.processed_count,
                    "totalCount": update.total_count,
                    "fileName": update.current_path.name,
                }
            )

        result = self.workflow.scan_folder(
            root, on_progress=progress, cancellation_token=token, resolve_spectral_profiles=False
        )
        return {**self._library(), "cancelled": result.cancelled}

    def _generate(self, params: dict[str, Any], token: ScanCancellationToken, emit: Progress) -> dict[str, Any]:
        count = params.get("targetTrackCount")
        if type(count) is not int or not 2 <= count <= 100:
            raise BackendError("invalid_params", "Track count must be an integer from 2 to 100")
        name = _text(params.get("name", "Prepared set"), "playlist name")
        self.invalidate_review()
        records = self._records()
        try:
            intent = make_intent(params, name, self._track_paths, records)
        except ValueError as exc:
            raise BackendError("invalid_params", str(exc)) from exc
        if len(records) < 2:
            raise BackendError("insufficient_tracks", "Scan at least two tagged tracks before preparing a set")

        def checkpoint(phase: str) -> None:
            if token.is_cancelled:
                raise BackendError("cancelled", "Preparation cancelled")
            emit(
                {
                    "phase": "prep",
                    "processedCount": ("safe", "balanced", "adventurous", "complete").index(phase),
                    "totalCount": 3,
                }
            )

        generation_binding = self.review_actions.capture_plan(records)
        plan = generate_plan(
            records,
            intent,
            checkpoint,
            loudness_band=self.preferences.loudness_band(),
            spectral_cohesion=self.preferences.spectral_cohesion(),
        )
        if token.is_cancelled:
            raise BackendError("cancelled", "Preparation cancelled")
        plan_id = str(uuid4())
        self.review_actions.bind_plan(plan_id, generation_binding)
        self.plan, self.plan_id = plan, plan_id
        return self._select({"planId": self.plan_id, "variant": "balanced"}, token)

    def _select(self, params: dict[str, Any], token: ScanCancellationToken) -> dict[str, Any]:
        plan_id, variant_name = params.get("planId"), params.get("variant")
        try:
            if not isinstance(plan_id, str) or str(UUID(plan_id)) != plan_id:
                raise ValueError
        except (ValueError, AttributeError) as exc:
            raise BackendError("invalid_params", "Invalid plan identity") from exc
        if self.plan is None or plan_id != self.plan_id:
            raise BackendError("stale_plan", "Generate a current plan before selecting a variant")
        if not isinstance(variant_name, str) or variant_name not in VARIANT_NAMES:
            raise BackendError("invalid_params", "Invalid Prep variant")
        if token.is_cancelled:
            self.invalidate_review()
            raise BackendError("cancelled", "Preparation cancelled")
        self.review_actions.verify_plan(plan_id)
        variant = next(item for item in self.plan.variants if item.name == variant_name)
        applications = {
            item.name: build_prep_copilot_variant_application(cast(PrepCopilotVariantLike, item))
            for item in self.plan.variants
        }
        self.review = applications[variant.name]
        self.review_id = str(uuid4())
        self.review_blocked = bool(variant.blockers) or not variant.recommendation.ordered_tracks
        return self.review_actions.bind(
            {
                "planId": self.plan_id,
                "variants": [
                    {
                        "name": item.name,
                        "description": item.description,
                        "trackCount": len(item.recommendation.ordered_tracks),
                        "readiness": item.readiness.status,
                        "warnings": item.warnings,
                        "blockers": item.blockers,
                        "qualityScore": applications[item.name].quality_report.average_transition_score,
                    }
                    for item in self.plan.variants
                ],
                "reviewId": self.review_id,
                "name": self.plan.intent.name,
                "variant": variant.name,
                "tracks": [_public_track(track) for track in variant.recommendation.ordered_tracks],
                "warnings": variant.warnings,
                "blockers": variant.blockers,
                "qualityScore": self.review.quality_report.average_transition_score,
                "readiness": self.review.readiness_report.status,
            }
        )
