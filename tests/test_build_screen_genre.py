"""The Build screen lets the DJ pick the genre a set is drawn from.

Genre used to be inferred from the anchor and only honoured by `same_genre`, so
locking a set to one genre meant giving up its energy shape. A DJ playing
30-minute blocks changes genre between them, which is exactly what that refuses.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from xfinaudio.desktop.screens.build_screen import ANY_GENRE, BuildScreen


def test_the_selector_offers_any_genre_first(qapp: QApplication) -> None:
    screen = BuildScreen()

    screen.set_available_genres(["Rock", "House & Electronic"])

    assert screen.genre_combo.itemText(0) == ANY_GENRE
    assert screen.selected_genre() is None, "the default must not silently narrow the library"


def test_the_selector_lists_the_genres_it_is_given(qapp: QApplication) -> None:
    screen = BuildScreen()

    screen.set_available_genres(["Rock", "House & Electronic", "Rock"])

    listed = [screen.genre_combo.itemText(index) for index in range(screen.genre_combo.count())]
    assert listed == [ANY_GENRE, "House & Electronic", "Rock"], "sorted, de-duplicated, 'any' first"


def test_choosing_a_genre_is_reported_to_the_caller(qapp: QApplication) -> None:
    screen = BuildScreen()
    screen.set_available_genres(["Rock", "House & Electronic"])

    screen.genre_combo.setCurrentIndex(screen.genre_combo.findText("Rock"))

    assert screen.selected_genre() == "Rock"


def test_the_choice_survives_a_library_refresh(qapp: QApplication) -> None:
    """Re-scanning must not silently reset the set the DJ is building."""
    screen = BuildScreen()
    screen.set_available_genres(["Rock", "House & Electronic"])
    screen.genre_combo.setCurrentIndex(screen.genre_combo.findText("Rock"))

    screen.set_available_genres(["Rock", "House & Electronic", "Country"])

    assert screen.selected_genre() == "Rock"


def test_a_genre_that_disappears_falls_back_to_any(qapp: QApplication) -> None:
    screen = BuildScreen()
    screen.set_available_genres(["Rock"])
    screen.genre_combo.setCurrentIndex(screen.genre_combo.findText("Rock"))

    screen.set_available_genres(["House & Electronic"])

    assert screen.selected_genre() is None
