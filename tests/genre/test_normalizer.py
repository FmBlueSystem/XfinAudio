"""Tests for the genre normalizer (PR1).

Covers spec Requirement 1, Scenarios 1.1, 1.2 and 1.3.
"""

from __future__ import annotations

from xfinaudio.genre.normalizer import UNMAPPED, GenreNormalizer


def test_known_style_maps_to_canonical_genre() -> None:
    normalizer = GenreNormalizer.default()

    assert normalizer.normalize("Tech House") == "Tech House"


def test_alias_and_case_variants_map_to_same_canonical() -> None:
    normalizer = GenreNormalizer.default()

    results = {
        normalizer.normalize("tech-house"),
        normalizer.normalize("Tech-House"),
        normalizer.normalize("TECH HOUSE"),
        normalizer.normalize("  tech   house  "),
    }

    assert results == {"Tech House"}


def test_canonical_label_normalizes_to_itself() -> None:
    normalizer = GenreNormalizer.default()

    assert normalizer.normalize("Drum & Bass") == "Drum & Bass"


def test_unknown_label_is_unmapped() -> None:
    normalizer = GenreNormalizer.default()

    assert normalizer.normalize("qwerty noise") == UNMAPPED


def test_empty_label_is_unmapped_without_raising() -> None:
    normalizer = GenreNormalizer.default()

    assert normalizer.normalize("") == UNMAPPED
    assert normalizer.normalize("   ") == UNMAPPED


def test_crosswalk_alias_maps_to_canonical() -> None:
    # Discogs/MB style raw labels should resolve through the crosswalk.
    normalizer = GenreNormalizer.default()

    assert normalizer.normalize("techno") == "Techno"
    assert normalizer.normalize("dnb") == "Drum & Bass"
