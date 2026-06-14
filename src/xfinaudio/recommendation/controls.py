"""DJ control constraints for playlist recommendation."""

from __future__ import annotations

from collections.abc import Set as AbstractSet

from pydantic import BaseModel, ConfigDict, Field, model_validator

from xfinaudio.library.models import TrackRecord


class DJControls(BaseModel):
    """User-selected constraints applied before playlist sequencing."""

    model_config = ConfigDict(frozen=True)

    locked_paths: AbstractSet[str] = Field(default_factory=set)
    excluded_paths: AbstractSet[str] = Field(default_factory=set)
    start_path: str | None = None
    end_path: str | None = None
    manual_order_paths: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_no_invalid_overlaps(self) -> DJControls:
        """Reject constraints that cannot be applied together."""
        if self.locked_paths & self.excluded_paths:
            raise ValueError("excluded paths cannot overlap locked paths")
        if self.start_path is not None and self.start_path in self.excluded_paths:
            raise ValueError("excluded paths cannot contain start_path")
        if self.end_path is not None and self.end_path in self.excluded_paths:
            raise ValueError("excluded paths cannot contain end_path")
        if len(self.manual_order_paths) != len(set(self.manual_order_paths)):
            raise ValueError("manual order paths cannot contain duplicates")
        return self


class AppliedControls(BaseModel):
    """Resolved control metadata after applying constraints to tracks."""

    model_config = ConfigDict(frozen=True)

    candidate_tracks: list[TrackRecord]
    manual_prefix: list[TrackRecord]
    locked_paths: list[str]
    excluded_paths: list[str]
    start_path: str | None
    end_path: str | None

    def summary(self) -> dict[str, object]:
        """Return a stable dictionary summary suitable for UI and API results."""
        return {
            "locked_paths": self.locked_paths,
            "excluded_paths": self.excluded_paths,
            "manual_order_paths": [track.path for track in self.manual_prefix],
            "start_path": self.start_path,
            "end_path": self.end_path,
        }


def apply_controls(tracks: list[TrackRecord], controls: DJControls | None = None) -> AppliedControls:
    """Apply DJ constraints and return candidate tracks plus resolved metadata."""
    controls = controls or DJControls()
    by_path = {track.path: track for track in tracks}
    _validate_known_paths(by_path, controls)

    candidate_tracks = [track for track in tracks if track.path not in controls.excluded_paths]
    manual_prefix = [
        by_path[path] for path in controls.manual_order_paths if path in by_path and path not in controls.excluded_paths
    ]
    manual_paths = {track.path for track in manual_prefix}
    ordered_candidates = [*manual_prefix, *(track for track in candidate_tracks if track.path not in manual_paths)]

    return AppliedControls(
        candidate_tracks=ordered_candidates,
        manual_prefix=manual_prefix,
        locked_paths=sorted(controls.locked_paths),
        excluded_paths=sorted(controls.excluded_paths),
        start_path=controls.start_path,
        end_path=controls.end_path,
    )


def _validate_known_paths(by_path: dict[str, TrackRecord], controls: DJControls) -> None:
    for label, path in (("start_path", controls.start_path), ("end_path", controls.end_path)):
        if path is not None and path not in by_path:
            raise ValueError(f"Unknown {label}: {path}")
    for path in sorted(controls.manual_order_paths):
        if path not in by_path:
            raise ValueError(f"Unknown manual_order_path: {path}")
    for path in sorted(controls.locked_paths):
        if path not in by_path:
            raise ValueError(f"Unknown locked_path: {path}")


__all__ = ["AppliedControls", "DJControls", "apply_controls"]
