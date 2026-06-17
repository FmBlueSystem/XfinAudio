"""Structured, deterministic provenance for how a playlist was constructed.

The build log is a read-only audit artifact: it records each construction stage with its
input/output/dropped counts, plus the per-adjacency genre relationship of the final sequence. It
never mutates audio, the library, or any Serato file — it is derived purely from the recommendation
pipeline's own counts and the ordered tracks.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.scoring import normalize_genre_tokens

GenreRelation = Literal["same", "overlap", "cross", "unknown"]


class BuildStage(BaseModel):
    """One stage of playlist construction with how many tracks entered, left, and were dropped."""

    model_config = ConfigDict(frozen=True)

    name: str
    input_count: int
    output_count: int
    dropped: int
    reason: str = ""


class TransitionGenreRelation(BaseModel):
    """Genre relationship between two adjacent tracks in the final sequence."""

    model_config = ConfigDict(frozen=True)

    order: int
    from_track: str
    to_track: str
    relation: GenreRelation


class PlaylistBuildLog(BaseModel):
    """Full provenance record of one recommendation build."""

    model_config = ConfigDict(frozen=True)

    strategy: str
    optimizer: str
    pool_size: int
    stages: list[BuildStage]
    genre_relations: list[TransitionGenreRelation]
    cross_genre_count: int
    final_track_count: int
    warnings: list[str]


def _classify(left_tokens: set[str], right_tokens: set[str]) -> GenreRelation:
    if not left_tokens or not right_tokens:
        return "unknown"
    if left_tokens == right_tokens:
        return "same"
    if left_tokens & right_tokens:
        return "overlap"
    return "cross"


def build_genre_relations(ordered_tracks: list[TrackRecord]) -> list[TransitionGenreRelation]:
    """Classify each adjacency by its shared genre tokens.

    ``same`` = identical token sets, ``overlap`` = some shared token, ``cross`` = disjoint genres,
    ``unknown`` = at least one side has no genre.
    """
    relations: list[TransitionGenreRelation] = []
    for order, (left, right) in enumerate(zip(ordered_tracks, ordered_tracks[1:], strict=False), start=1):
        relation = _classify(normalize_genre_tokens(left.genre), normalize_genre_tokens(right.genre))
        relations.append(
            TransitionGenreRelation(
                order=order,
                from_track=left.title or left.path,
                to_track=right.title or right.path,
                relation=relation,
            )
        )
    return relations


def count_cross_genre(relations: list[TransitionGenreRelation]) -> int:
    """Number of adjacencies whose two tracks share no genre token."""
    return sum(1 for relation in relations if relation.relation == "cross")


__all__ = [
    "BuildStage",
    "GenreRelation",
    "PlaylistBuildLog",
    "TransitionGenreRelation",
    "build_genre_relations",
    "count_cross_genre",
]
