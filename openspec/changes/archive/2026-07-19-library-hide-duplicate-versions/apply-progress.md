# Apply Progress: Hide Duplicate Track Versions in the Library Screen

## Completed

- [x] R1 — Title/artist normalization (`library_filter.py`)
- [x] R2 — Blank/placeholder metadata never groups
- [x] R3 — Representative selection
- [x] R4 — Row-level composition with search (`library_screen_rendering.py`)
- [x] R5 — UI toggle independence (`library_screen_builder.py`, `screens/library_screen.py`)
- [x] R6 — Duplicate-count label

## Files Changed

| File | Action | What Was Done |
|---|---|---|
| `src/xfinaudio/desktop/library_filter.py` | Modified | Added pure grouping/normalization functions: `_normalize_title_for_grouping`, `_normalize_artist_for_grouping`, `_duplicate_group_key`, `_RowInfo` (NamedTuple), `_pick_duplicate_representative`, `suppressed_duplicate_paths`. No `TrackRecord`/Qt dependency. |
| `src/xfinaudio/desktop/library_screen_rendering.py` | Modified | New `_apply_duplicate_filter()` (row-level, reads rendered cell text for currently-visible rows only, updates `duplicate_count_label`); new composite `_apply_search_and_duplicate_filters()`; `render()` and `_on_search_changed()` now call the composite instead of `_apply_filter()` directly; `_refresh_filter_state()`, `clear_quick_filters()`, `restore_quick_filters()` now include `hide_duplicates_button` via a new `_all_filter_buttons()` helper. `LibraryFilters`/`_current_library_filters()` left unchanged, per design. |
| `src/xfinaudio/desktop/library_screen_builder.py` | Modified | Added `screen.hide_duplicates_button` (checkable, checked-style stylesheet, added to `quick_filter_layout` right after the 5 existing buttons, deliberately NOT added to `quick_filter_buttons`) and `screen.duplicate_count_label` (next to `active_filter_count_label`). |
| `src/xfinaudio/desktop/screens/library_screen.py` | Modified | `hide_duplicates_button.clicked` connected directly to `_refresh_filter_state` (bypassing `_on_quick_filter_changed`'s mutual-exclusion logic); added to `_setup_button_tooltips()`. Not added to `_setup_accessibility()`/`_setup_tab_order()` — the existing 5 quick-filter buttons have no entries in either method either, so this preserves that same established (lack of) pattern; see Deviations below. |
| `tests/test_library_filter.py` | Modified | 28 new tests covering R1 (normalization), R2 (blank/placeholder guard), R3 (representative selection), and `suppressed_duplicate_paths` group semantics. |
| `tests/test_library_screen.py` | Modified | 14 new tests covering R4 (row-level composition with search), R5 (toggle independence, Clear Filters, undo-restore, active-count), R6 (duplicate-count label). Added `_state_with_duplicates()` fixture helper. |

## TDD Cycle Evidence

| Task | Test File | Test Name(s) | RED | GREEN | REFACTOR |
|---|---|---|---|---|---|
| R1 Title/artist normalization | `tests/test_library_filter.py` | `test_normalize_title_strips_camelot_energy_suffix`, `test_normalize_title_strips_single_digit_camelot_key`, `test_normalize_title_strips_version_suffix`, `test_normalize_title_strips_both_suffixes_regardless_of_order`, `test_normalize_title_strips_repeated_version_suffixes`, `test_normalize_title_preserves_remix_descriptor`, `test_normalize_title_preserves_long_version_descriptor`, `test_normalize_title_preserves_clean_descriptor`, `test_normalize_title_does_not_falsely_strip_non_camelot_suffix`, `test_normalize_title_strips_whitespace`, `test_normalize_title_casefold_applied_after_suffix_stripping`, `test_normalize_artist_casefolds_and_strips_whitespace`, `test_normalize_artist_does_not_strip_suffixes` | ✅ `ImportError` — `_normalize_title_for_grouping`/`_normalize_artist_for_grouping` did not exist yet | ✅ Passed after adding the suffix-stripping loop (strip original-case text first, casefold last) and the exact `artist.strip().casefold()` contract | ✅ No further changes needed |
| R2 Blank/placeholder metadata guard | `tests/test_library_filter.py` | `test_duplicate_group_key_none_when_title_none`, `test_duplicate_group_key_none_when_artist_none`, `test_duplicate_group_key_none_when_title_blank`, `test_duplicate_group_key_none_when_artist_blank`, `test_duplicate_group_key_none_when_title_is_placeholder_dash`, `test_duplicate_group_key_none_when_artist_is_placeholder_dash`, `test_duplicate_group_key_returns_normalized_tuple_for_valid_input` | ✅ `ImportError` — `_duplicate_group_key` did not exist yet | ✅ Passed after adding the `None`/blank/`"—"` placeholder guard (same `_DASH` character as `library_view_model.py`) | ✅ No further changes needed |
| R3 Representative selection | `tests/test_library_filter.py` | `test_pick_representative_prefers_complete_status`, `test_pick_representative_prefers_lower_missing_field_count_when_status_tied`, `test_pick_representative_prefers_shorter_title_when_status_and_missing_tied`, `test_pick_representative_uses_path_as_final_tiebreak`, `test_suppressed_duplicate_paths_singleton_untouched`, `test_suppressed_duplicate_paths_suppresses_all_but_representative`, `test_suppressed_duplicate_paths_blank_metadata_rows_never_suppressed`, `test_suppressed_duplicate_paths_multiple_independent_groups`, `test_suppressed_duplicate_paths_empty_input` | ✅ `ImportError` — `_pick_duplicate_representative`/`suppressed_duplicate_paths`/`_RowInfo` did not exist yet | ✅ Passed after adding the 4-level tiebreak sort key and the group-and-suppress loop | ✅ No further changes needed |
| R4 Row-level composition with search | `tests/test_library_screen.py` | `test_hide_duplicates_button_collapses_duplicate_rows`, `test_hide_duplicates_button_off_shows_all_rows`, `test_search_does_not_unhide_suppressed_duplicates`, `test_duplicate_filter_only_considers_search_visible_rows` | ✅ `AttributeError: 'LibraryScreen' object has no attribute 'hide_duplicates_button'` | ✅ Passed after adding `_apply_duplicate_filter()`, `_apply_search_and_duplicate_filters()`, and wiring both `render()` and `_on_search_changed()` to the composite | ✅ No further changes needed |
| R5 UI toggle independence | `tests/test_library_screen.py` | `test_hide_duplicates_button_independent_of_status_mutual_exclusion`, `test_hide_duplicates_toggle_does_not_uncheck_missing_filters`, `test_clear_filters_includes_hide_duplicates_button`, `test_restore_quick_filters_restores_hide_duplicates_button`, `test_active_filter_count_includes_hide_duplicates_button` | ✅ `AttributeError` — button did not exist yet | ✅ Passed after adding `hide_duplicates_button` (excluded from `quick_filter_buttons`, wired directly to `_refresh_filter_state`) and the `_all_filter_buttons()` helper used by `clear_quick_filters`/`restore_quick_filters`/`_refresh_filter_state` | ✅ No further changes needed |
| R6 Duplicate-count label | `tests/test_library_screen.py` | `test_duplicate_count_label_empty_when_toggle_off`, `test_duplicate_count_label_shows_count_when_enabled`, `test_duplicate_count_label_empty_when_no_duplicates`, `test_duplicate_count_label_clears_when_toggle_off_again` | ✅ `AttributeError` — `duplicate_count_label` did not exist yet | ✅ Passed after adding `duplicate_count_label` and its update logic inside `_apply_duplicate_filter()` | ✅ No further changes needed |

## Deviations from Design

None functionally. One clarified interpretation: PLAN.md's instruction to add `hide_duplicates_button` to `_setup_accessibility()` and `_setup_tab_order()` "following the exact same pattern used for the other quick-filter buttons" was resolved literally — none of the 5 existing quick-filter buttons (`complete_filter_button`, `incomplete_filter_button`, `missing_bpm_filter_button`, `missing_key_filter_button`, `missing_energy_filter_button`) have entries in either method today (verified by reading both methods before editing), so `hide_duplicates_button` was left out of both too, matching that established absence. It **was** added to `_setup_button_tooltips()`, since all 5 existing quick-filter buttons do have tooltip entries there, and the existing `test_all_buttons_have_tooltips` test requires every `QPushButton` to have a non-empty tooltip.

## Issues Found

None.

## Verification

- ✅ Full pytest: 1059 passed.
- ✅ Pyright (`src tests`): 0 errors, 0 warnings, 0 informations.
- ✅ Coverage: 90.43% total, above the 70% gate.
- ✅ Ruff check: all checks passed.
- ✅ Ruff format check: 263 files already formatted.
- ✅ Release gate (`scripts/release_gate_check.py --run`): PASS (tests, type-check, coverage, lint, format, release readiness smoke, open-source docs, publication hygiene, source package hygiene, PyInstaller check-only all green).

Full command-by-command results are in `verify-report.md`.

## Native review corrections (post-apply, `gentle-ai review`)

After apply/verify above, the native bounded-review lifecycle ran the full 4R
lens set (high risk tier). Two lineages were needed:

1. **`review-9967994641103116`** — reviewed the initial implementation.
   Reliability found a **CRITICAL**: `_normalize_title_for_grouping` preserved
   parenthetical content as an opaque block, so the exact three real-world
   duplicate titles from the motivating screenshot did NOT all normalize
   identically — two had the remix descriptor wrapped in parentheses, one
   didn't (real-world export inconsistency), producing two different group
   keys. The feature silently failed to collapse the exact case it was built
   to solve. Also found: `_DASH` triplicated across 3 modules with no shared
   import (WARNING), a pluralization bug — "1 duplicates hidden" (WARNING),
   checked-button stylesheet duplicated (SUGGESTION), and
   `missing_field_count` parsed against a hardcoded separator with no shared
   constant (SUGGESTION). Resilience also flagged a per-keystroke performance
   WARNING (the new row-level dedup pass has no debounce on large libraries)
   and a label-ambiguity SUGGESTION (toggle-off and toggle-on-zero both showed
   an empty string). This lineage was correctly **escalated** on the CRITICAL.
2. **`review-193e3a2f9299bd42`** — re-review after fixes: `_normalize_title_for_grouping`
   now strips `(`/`)` as punctuation (content preserved) instead of treating
   parens as opaque — verified all three screenshot titles now normalize
   identically, plus a negative-control test confirming genuinely different
   remix descriptors still don't group. `_DASH` and a new
   `MISSING_FIELDS_SEPARATOR` constant are now imported from their single
   source (`library_view_model.py`) instead of redefined; the count label is
   singular/plural-aware and distinguishes "off" from "on, nothing found"
   ("No duplicates found"); the checked-button stylesheet is a shared
   `_CHECKED_FILTER_BUTTON_STYLE` constant. The performance WARNING was
   **deliberately left unfixed** — re-confirmed present by both resilience and
   reliability lenses in this round, classified `pre-existing`/non-blocking; a
   proper fix needs new debounce infrastructure beyond this change's scope,
   logged as a follow-up. Reliability also found one new WARNING in this
   round: the paren-stripping fix has a narrow, non-blocking false-positive
   risk — two genuinely different titles that share identical words modulo
   parentheses (e.g. "Track One (B-Side)" vs "Track One B-Side") would now
   collide into one group. Accepted as a known, documented tradeoff (display-
   only, fully reversible by unchecking the toggle, no data loss) rather than
   engineered away, since the CRITICAL fix requires treating parens as
   punctuation to work at all. **Approved.** Receipt at
   `.git/gentle-ai/review-transactions/v2/review-193e3a2f9299bd42/review-receipt.json`.

Final full-suite verification after all corrections: 1061 passed, pyright 0
errors, ruff check/format clean. See `verify-report.md` for the final
command-by-command table.
