# Design: Hide Duplicate Track Versions in the Library Screen

## Decision question

Where should duplicate-suppression logic live, and how should it compose with the Library screen's existing search/filter mechanisms without breaking either?

## Alternatives considered (Arbor-style)

### Where dedup lives

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Data layer — inside `LibraryViewModel.tracks_for_display`, via a new `LibraryFilters.hide_duplicates` flag | Matches the existing `search_query`/`status_filter`/`missing_field_filter` sequential-AND pattern already in that function; simplest mental model. | **Broken by a real architectural fact, found via Codex Round 1 code reading**: the Library screen's actual live search does NOT run through this function's `search_query` path — `_current_library_filters()` never populates it, so that branch is dead code in production. Real search is `_apply_filter()`, a row-level pass on the already-rendered `QTableWidget`, called at the end of every `render()`. If dedup ran at the data layer (before rows are ever rendered), a suppressed duplicate's row would never exist in the table at all — so a later search for text that only matches that suppressed row would show zero results, permanently, not just transiently. | Rejected. |
| B. Row level — a new `_apply_duplicate_filter()` pass, structurally parallel to `_apply_filter()`/`_apply_constraint_colors()`, run after search on whatever's already visible | Composes correctly with the real search mechanism by construction — dedup only ever considers rows the user's current search already matched, so it can never make a genuine match unfindable. Matches this file's existing pattern of reading rendered `QTableWidgetItem` text back out (same technique `_apply_constraint_colors` already uses for the Path column). | Requires re-deriving `_RowInfo` (title/artist/status/missing-field-count/path) from rendered cell text instead of `TrackRecord` objects directly. | **Selected.** |

### Search/dedup ordering safety

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Wire `_apply_duplicate_filter()` only into `render()` | Simple, one call site. | **Found broken in Round 2**: `_on_search_changed()` calls `_apply_filter()` directly on every keystroke, bypassing `render()` entirely — so typing would desync the two passes, un-hiding previously-suppressed duplicates until the next full render happened to fire. | Rejected. |
| B. One composite `_apply_search_and_duplicate_filters()` calling both passes in order, called from both `render()` and `_on_search_changed()` | The two passes can never run out of sync — every code path that used to call `_apply_filter()` alone now calls the composite. | One extra method, trivial cost. | **Selected.** |

## Architecture impact

- `library_filter.py` gains pure functions: `_normalize_title_for_grouping`, `_normalize_artist_for_grouping`, `_duplicate_group_key`, `_pick_duplicate_representative`, `suppressed_duplicate_paths`. None depend on `TrackRecord` or Qt — parameterized on plain strings/a local `_RowInfo` named tuple, so they're testable in isolation and reusable at either layer if ever needed.
- `library_screen_rendering.py`: new `_apply_duplicate_filter()` (builds `_RowInfo` from rendered cell text for currently-visible rows only, calls `suppressed_duplicate_paths`, hides the result); new composite `_apply_search_and_duplicate_filters()`; `render()` and `_on_search_changed()` updated to call the composite instead of `_apply_filter()` directly.
- `library_screen_builder.py`: new `hide_duplicates_button` (checkable, NOT in the `quick_filter_buttons` mutual-exclusion tuple) and `duplicate_count_label`.
- `screens/library_screen.py`: `hide_duplicates_button` added to `_setup_button_tooltips`, `_setup_accessibility`, `_setup_tab_order`, and to the button set covered by `clear_quick_filters`/`restore_quick_filters`/`_refresh_filter_state`'s active-count sum.
- `LibraryFilters`/`library_filter_state.py`: **unchanged** — the originally-planned `hide_duplicates` field/flag plumbing through `library_filters_from_flags` was dropped once dedup moved to the row level; `_apply_duplicate_filter()` reads `self.hide_duplicates_button.isChecked()` directly, the same way `_apply_filter()` reads `self._filter_query` directly.

## Affected files

- `src/xfinaudio/desktop/library_filter.py`
- `src/xfinaudio/desktop/library_screen_rendering.py`
- `src/xfinaudio/desktop/library_screen_builder.py`
- `src/xfinaudio/desktop/screens/library_screen.py`
- `tests/test_library_filter.py`
- `tests/test_library_screen.py` / `tests/test_library_screen_boundaries.py` (wiring/composition tests)

## Safety

- No audio mutation.
- No DSP scope expansion.
- No live Serato Database V2 writes.
- Display-only: no scanned data, database rows, or files on disk are mutated — this is a pure row-hiding filter.

## Known correction history (grill + adversarial review)

1. **Normalization order vs. regex casing** (Round 4): suffix-stripping regex is written against real-case text (`"Energy"`, uppercase Camelot letters); the plan originally lowercased before stripping, which would have silently disabled suffix matching. Fixed: strip first, casefold last.
2. **Blank-metadata guard needs the display placeholder, not just `None`** (Round 2): `_to_display_row()` already converts `None`/blank to the `"—"` placeholder before rendering, so the row-level reader never sees `None` — the placeholder string itself must be treated as blank too.
3. **`_RowInfo`'s missing-field count needs to be pre-computed, not parsed from formatted text** (Round 3): ranking must never parse the rendered `"bpm, camelot_key"`-style string; compute `missing_field_count: int` once at `_RowInfo` construction (`0` for the `"—"` placeholder, else split-count on `", "`, matching `_fmt_missing`'s own join separator exactly).
4. **Artist normalization needed an explicit contract** (Round 3): originally left implicit; locked to `artist.strip().casefold()`, no suffix stripping.
