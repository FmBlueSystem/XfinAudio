"""Tests for the layer-neutral duplicate-grouping keys.

Spec: odd/tasks/xfinaudio-serato-seed-ux.md, S7 — a generated set holds one
version per song. The strict playlist key recognises the user's live-observed
rows (punctuation, accents, a leading article on the artist, and a blank artist
carried by an "Artist - Title" title) while the conservative Library-display key
stays exactly as it was.
"""

from __future__ import annotations

from xfinaudio.library.duplicate_grouping import (
    duplicate_group_key,
    playlist_duplicate_group_key,
)

# Verbatim rows from the user's screenshot (S7).
YMCA_ROWS = [
    ("YMCA", "The Village People"),
    ("Y.M.C.A.", "The Village People"),
    ("YMCA (Hot Tracks)", "Village People"),
    ("Y.M.C.A. (DJ Edit)", "Village People"),
]

KILLERS_EDIT_ROW = ("The Killers - All These Things I've Done (Edit by Mark Roberts)", "")
KILLERS_PLAIN_ROW = ("The Killers - All These Things I've Done", "")
KILLERS_TITLED_ROW = ("All These Things I've Done", "The Killers")


def test_s7_ymca_rows_share_one_key_with_blank_artist_derivation():
    keys = {playlist_duplicate_group_key(title, artist) for title, artist in YMCA_ROWS}
    assert len(keys) == 1
    assert None not in keys


def test_s7_killers_rows_share_one_key_including_the_artist_title_row():
    edit_row = playlist_duplicate_group_key(*KILLERS_EDIT_ROW)
    plain_row = playlist_duplicate_group_key(*KILLERS_PLAIN_ROW)
    titled_row = playlist_duplicate_group_key(*KILLERS_TITLED_ROW)
    assert edit_row is not None
    assert edit_row == plain_row == titled_row


def test_blank_artist_title_row_matches_artist_field_row():
    derived = playlist_duplicate_group_key("Stevie Wonder - Higher Ground [DJ Beats]", "")
    explicit = playlist_duplicate_group_key("Higher Ground", "Stevie Wonder")
    assert derived is not None
    assert derived == explicit


def test_accents_fold_to_the_same_key():
    accented = playlist_duplicate_group_key("Brújula", "Los Aterciopelados")
    plain = playlist_duplicate_group_key("Brujula", "Aterciopelados")
    assert accented is not None
    assert accented == plain


def test_same_title_with_different_artists_stays_distinct():
    first = playlist_duplicate_group_key("YMCA", "The Village People")
    second = playlist_duplicate_group_key("YMCA", "Village People Tribute Band")
    assert first is not None and second is not None
    assert first != second


def test_blank_artist_title_without_separator_returns_none():
    assert playlist_duplicate_group_key("Higher Ground", "") is None
    assert playlist_duplicate_group_key("Higher Ground", None) is None


def test_ymca_and_ymca_part_two_stay_distinct():
    original = playlist_duplicate_group_key("YMCA", "The Village People")
    part_two = playlist_duplicate_group_key("YMCA Pt 2", "Village People")
    assert original is not None and part_two is not None
    assert original != part_two


def test_artist_literally_named_the_the_keeps_a_non_empty_key():
    key = playlist_duplicate_group_key("This Is The Day", "The The")
    assert key is not None
    # One article is stripped and never to nothing: "The The" keeps "the".
    assert key[0] == "the"
    # A blank artist is a different thing entirely: it has no key here.
    assert playlist_duplicate_group_key("This Is The Day", "") is None


def test_conservative_library_key_is_unchanged_for_the_s7_rows():
    # The Library screen's display filter must keep showing every version, so
    # this key still strips app-generated suffixes and parens-as-punctuation
    # only: no punctuation/accent folding, no article stripping, no artist
    # derived from the title.
    assert duplicate_group_key("YMCA", "The Village People") == ("the village people", "ymca")
    assert duplicate_group_key("Y.M.C.A.", "The Village People") == ("the village people", "y.m.c.a.")
    assert duplicate_group_key("YMCA (Hot Tracks)", "Village People") == ("village people", "ymca hot tracks")
    assert duplicate_group_key("Y.M.C.A. (DJ Edit)", "Village People") == ("village people", "y.m.c.a. dj edit")
    assert duplicate_group_key(*KILLERS_EDIT_ROW) is None
    assert duplicate_group_key(*KILLERS_PLAIN_ROW) is None
