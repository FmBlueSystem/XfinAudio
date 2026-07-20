"""Tests for library.duplicate_grouping — the layer-neutral duplicate-group core.

These functions are the Qt-free, TrackRecord-agnostic relocation of the
duplicate-grouping logic previously private to `desktop/library_filter.py`
(see design.md Decision 3a). `desktop/library_filter.py` delegates to this
module; `recommendation/candidate_pool.py` calls it directly with
`placeholder=None`.
"""

from __future__ import annotations

from xfinaudio.library.duplicate_grouping import (
    duplicate_group_key,
    duplicate_representative_sort_key,
    normalize_artist_for_grouping,
    normalize_title_for_grouping,
    normalize_title_for_playlist_grouping,
    playlist_duplicate_group_key,
)

# ---------------------------------------------------------------------------
# normalize_title_for_grouping / normalize_artist_for_grouping
# ---------------------------------------------------------------------------


def test_normalize_title_strips_camelot_energy_suffix():
    assert normalize_title_for_grouping("Right On Track - 12A - Energy 7") == "right on track"


def test_normalize_title_strips_version_suffix():
    assert normalize_title_for_grouping("Right On Track (v2)") == "right on track"


def test_normalize_title_strips_both_suffixes_regardless_of_order():
    assert normalize_title_for_grouping("Song - 8A - Energy 7 (v2)") == "song"
    assert normalize_title_for_grouping("Song (v2) - 8A - Energy 7") == "song"


def test_normalize_title_preserves_remix_descriptor_content_but_strips_parens():
    assert (
        normalize_title_for_grouping("Right On Track (kwikMIX by DJ Richie Rich)")
        == "right on track kwikmix by dj richie rich"
    )


def test_normalize_title_does_not_falsely_strip_non_camelot_suffix():
    assert normalize_title_for_grouping("Song - AB - Energy 7") == "song - ab - energy 7"


def test_normalize_artist_casefolds_and_strips_whitespace():
    assert normalize_artist_for_grouping("  DJ Name  ") == "dj name"
    assert normalize_artist_for_grouping("DJ NAME") == "dj name"


def test_normalize_artist_does_not_strip_suffixes():
    assert normalize_artist_for_grouping("DJ Name - 8A - Energy 7") == "dj name - 8a - energy 7"


# ---------------------------------------------------------------------------
# duplicate_group_key — Qt-free, placeholder-parametrized
# ---------------------------------------------------------------------------


def test_duplicate_group_key_none_when_title_none():
    assert duplicate_group_key(None, "Artist", placeholder="—") is None


def test_duplicate_group_key_none_when_artist_none():
    assert duplicate_group_key("Title", None, placeholder="—") is None


def test_duplicate_group_key_none_when_title_blank():
    assert duplicate_group_key("   ", "Artist", placeholder="—") is None


def test_duplicate_group_key_none_when_artist_blank():
    assert duplicate_group_key("Title", "   ", placeholder="—") is None


def test_duplicate_group_key_none_when_title_is_placeholder():
    assert duplicate_group_key("—", "Artist", placeholder="—") is None


def test_duplicate_group_key_none_when_artist_is_placeholder():
    assert duplicate_group_key("Title", "—", placeholder="—") is None


def test_duplicate_group_key_returns_normalized_tuple_for_valid_input():
    assert duplicate_group_key("Song - 8A - Energy 7", "  DJ Name  ", placeholder="—") == ("dj name", "song")


def test_duplicate_group_key_no_placeholder_check_when_placeholder_is_none():
    # `placeholder=None` (the recommendation-pool caller) means: no dash-literal
    # special case — only blank/None title or artist forces a singleton.
    assert duplicate_group_key("—", "Artist", placeholder=None) == ("artist", "—")


def test_duplicate_group_key_default_placeholder_is_none():
    assert duplicate_group_key("Song", "Artist") == ("artist", "song")


def test_duplicate_group_key_is_qt_free():
    import ast

    import xfinaudio.library.duplicate_grouping as module

    source = module.__file__
    assert source is not None
    with open(source, encoding="utf-8") as handle:
        tree = ast.parse(handle.read())

    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.append(node.module)
        elif isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)

    assert not any(name.startswith("xfinaudio.desktop") for name in imported_modules)
    assert not any(name.startswith("PyQt") for name in imported_modules)


# ---------------------------------------------------------------------------
# duplicate_representative_sort_key
# ---------------------------------------------------------------------------


def test_representative_sort_key_prefers_complete_status():
    complete_key = duplicate_representative_sort_key(
        is_complete=True, missing_field_count=2, title="Song", path="/a.mp3"
    )
    incomplete_key = duplicate_representative_sort_key(
        is_complete=False, missing_field_count=0, title="Song", path="/b.mp3"
    )
    assert complete_key < incomplete_key


def test_representative_sort_key_prefers_fewer_missing_fields_when_status_tied():
    fewer = duplicate_representative_sort_key(is_complete=True, missing_field_count=0, title="Song", path="/a.mp3")
    more = duplicate_representative_sort_key(is_complete=True, missing_field_count=2, title="Song", path="/b.mp3")
    assert fewer < more


def test_representative_sort_key_prefers_shorter_title_when_status_and_missing_tied():
    shorter = duplicate_representative_sort_key(is_complete=True, missing_field_count=0, title="Song", path="/b.mp3")
    longer = duplicate_representative_sort_key(
        is_complete=True, missing_field_count=0, title="Song Extended", path="/a.mp3"
    )
    assert shorter < longer


def test_representative_sort_key_uses_path_as_final_tiebreak():
    first = duplicate_representative_sort_key(is_complete=True, missing_field_count=0, title="Song", path="/a.mp3")
    second = duplicate_representative_sort_key(is_complete=True, missing_field_count=0, title="Song", path="/z.mp3")
    assert first < second


def test_representative_sort_key_matches_documented_tuple_shape():
    key = duplicate_representative_sort_key(is_complete=True, missing_field_count=1, title="Song", path="/a.mp3")
    assert key == (0, 1, len("Song"), "/a.mp3")
    key_incomplete = duplicate_representative_sort_key(
        is_complete=False, missing_field_count=1, title="Song", path="/a.mp3"
    )
    assert key_incomplete == (1, 1, len("Song"), "/a.mp3")


# ---------------------------------------------------------------------------
# Relocation regression (design.md Decision 3a, tasks.md B4): the desktop
# display filter must delegate to this module — imports only, identical
# output to the pre-relocation baseline. `tests/test_library_filter.py`
# itself stays untouched (per B1/B5/B15); this module is where the
# delegation is verified instead.
# ---------------------------------------------------------------------------


def test_library_filter_normalization_functions_delegate_to_this_module():
    from xfinaudio.desktop.library_filter import (
        _normalize_artist_for_grouping,
        _normalize_title_for_grouping,
    )

    assert _normalize_title_for_grouping is normalize_title_for_grouping
    assert _normalize_artist_for_grouping is normalize_artist_for_grouping


def test_library_filter_duplicate_group_key_matches_neutral_module_with_dash_placeholder():
    from xfinaudio.desktop.library_filter import _duplicate_group_key
    from xfinaudio.desktop.library_view_model import _DASH

    assert _duplicate_group_key("Song - 8A - Energy 7", "DJ Name") == duplicate_group_key(
        "Song - 8A - Energy 7", "DJ Name", placeholder=_DASH
    )
    assert _duplicate_group_key(_DASH, "Artist") is None
    assert duplicate_group_key(_DASH, "Artist", placeholder=_DASH) is None


def test_library_filter_pick_representative_uses_neutral_sort_key():
    from xfinaudio.desktop.library_filter import _pick_duplicate_representative, _RowInfo

    rows = [
        _RowInfo(title="Song Extended", artist="Artist", status="incomplete", missing_field_count=0, path="/b.mp3"),
        _RowInfo(title="Song", artist="Artist", status="incomplete", missing_field_count=0, path="/a.mp3"),
    ]
    assert _pick_duplicate_representative(rows).path == "/a.mp3"


# ---------------------------------------------------------------------------
# normalize_title_for_playlist_grouping / playlist_duplicate_group_key
# (maintainer decision 2026-07-20): the recommendation candidate pool uses a
# STRICTER key than the library display filter — parenthetical descriptor
# content is removed entirely, not just un-wrapped. The library display
# filter's `normalize_title_for_grouping` / `duplicate_group_key` are
# untouched by this addition.
# ---------------------------------------------------------------------------


def test_normalize_title_for_playlist_grouping_strips_camelot_energy_suffix():
    assert normalize_title_for_playlist_grouping("Still - 3B - Energy 3") == "still"


def test_normalize_title_for_playlist_grouping_strips_version_suffix():
    assert normalize_title_for_playlist_grouping("Right On Track (v2)") == "right on track"


def test_normalize_title_for_playlist_grouping_removes_parenthetical_content_entirely():
    # Live-observed regression pairs (maintainer decision 2026-07-20): distinct
    # parenthetical descriptors are the SAME song for playlist-pool purposes.
    assert normalize_title_for_playlist_grouping("Too Hot (Single Version)") == "too hot"
    assert normalize_title_for_playlist_grouping("Too Hot (Clean)") == "too hot"
    assert normalize_title_for_playlist_grouping("Too Hot") == "too hot"
    assert normalize_title_for_playlist_grouping('Se La (12" Version)') == "se la"
    assert normalize_title_for_playlist_grouping("Se La") == "se la"


def test_normalize_title_for_playlist_grouping_differs_from_conservative_key_on_descriptor_content():
    # The library display filter's conservative key keeps these DISTINCT
    # (descriptor content is preserved) — the playlist key collapses them.
    conservative_clean = normalize_title_for_grouping("Too Hot (Clean)")
    conservative_single = normalize_title_for_grouping("Too Hot (Single Version)")
    assert conservative_clean != conservative_single

    playlist_clean = normalize_title_for_playlist_grouping("Too Hot (Clean)")
    playlist_single = normalize_title_for_playlist_grouping("Too Hot (Single Version)")
    assert playlist_clean == playlist_single


def test_normalize_title_for_playlist_grouping_does_not_falsely_strip_non_camelot_suffix():
    assert normalize_title_for_playlist_grouping("Song - AB - Energy 7") == "song - ab - energy 7"


def test_normalize_title_for_playlist_grouping_distinct_songs_outside_parens_still_differ():
    assert normalize_title_for_playlist_grouping("Love On The Rocks") != normalize_title_for_playlist_grouping(
        "Love Me Tender"
    )


def test_playlist_duplicate_group_key_none_when_title_none():
    assert playlist_duplicate_group_key(None, "Artist") is None


def test_playlist_duplicate_group_key_none_when_artist_blank():
    assert playlist_duplicate_group_key("Title", "   ") is None


def test_playlist_duplicate_group_key_collapses_parenthetical_descriptor_variants():
    assert playlist_duplicate_group_key("Too Hot (Single Version)", "Glenn Jones") == playlist_duplicate_group_key(
        "Too Hot (Clean)", "Glenn Jones"
    )
    assert playlist_duplicate_group_key("Too Hot", "Glenn Jones") == playlist_duplicate_group_key(
        "Too Hot (Clean)", "Glenn Jones"
    )


def test_playlist_duplicate_group_key_matches_conservative_artist_normalization():
    assert playlist_duplicate_group_key("Song", "  DJ Name  ") == ("dj name", "song")


# ---------------------------------------------------------------------------
# CRITICAL 2 correction (native 4R review): a fully-parenthetical title (e.g.
# "(Intro)", "(Outro)") normalizes to an empty string under
# `normalize_title_for_playlist_grouping` — without a guard, distinct
# fully-parenthetical titles for the same artist would collide on the same
# `(artist, "")` key and falsely collapse.
# ---------------------------------------------------------------------------


def test_playlist_duplicate_group_key_none_when_normalized_title_is_fully_parenthetical():
    assert playlist_duplicate_group_key("(Intro)", "Artist") is None
    assert playlist_duplicate_group_key("(Outro)", "Artist") is None
