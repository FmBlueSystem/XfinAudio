"""Tests for the canonical genre taxonomy (PR1).

Covers spec Requirement 1, Scenarios 1.1 and 1.4.
"""

from __future__ import annotations

from xfinaudio.genre.taxonomy import Taxonomy, load_taxonomy

CORE_ELECTRONIC = (
    "House",
    "Techno",
    "Trance",
    "Drum & Bass",
    "Deep House",
    "Tech House",
    "Melodic House & Techno",
    "Peak Time Techno",
    "Progressive House",
)

# Scope decision (PR1): electronic + general genres.
CORE_GENERAL = (
    "Rock",
    "Pop",
    "Hip-Hop",
    "R&B",
    "World & Latin",
)


def test_load_taxonomy_returns_taxonomy() -> None:
    taxonomy = load_taxonomy()

    assert isinstance(taxonomy, Taxonomy)
    assert len(taxonomy.genres) > 0


def test_taxonomy_covers_core_electronic_tree() -> None:
    taxonomy = load_taxonomy()

    for genre in CORE_ELECTRONIC:
        assert taxonomy.is_canonical(genre), f"missing canonical electronic genre: {genre}"


def test_taxonomy_covers_general_genres() -> None:
    taxonomy = load_taxonomy()

    for genre in CORE_GENERAL:
        assert taxonomy.is_canonical(genre), f"missing canonical general genre: {genre}"


def test_tech_house_parent_is_house() -> None:
    taxonomy = load_taxonomy()

    assert taxonomy.parent_of("Tech House") == "House"


def test_top_level_genre_has_no_parent() -> None:
    taxonomy = load_taxonomy()

    assert taxonomy.parent_of("House") is None


def test_unknown_genre_is_not_canonical() -> None:
    taxonomy = load_taxonomy()

    assert taxonomy.is_canonical("qwerty noise") is False
    assert taxonomy.parent_of("qwerty noise") is None


def test_taxonomy_is_cached_singleton() -> None:
    assert load_taxonomy() is load_taxonomy()
