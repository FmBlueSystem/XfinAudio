# Verify Report: Hide Duplicate Track Versions in the Library Screen

## Verification commands (final, after native-review corrections)

| Command | Result |
|---|---|
| `uv run pytest -q` | PASS — 1061 passed |
| `uv run pyright src tests` | PASS — 0 errors, 0 warnings, 0 informations |
| `uv run pytest --cov --cov-fail-under=70 -q` | PASS — 90.42% total coverage (gate: 70%) |
| `uv run ruff check .` | PASS — all checks passed |
| `uv run ruff format --check .` | PASS — 263 files already formatted |
| `uv run python scripts/release_gate_check.py --run` | PASS — tests, type-check, coverage, lint, format, release readiness smoke, open-source publication docs, publication artifact hygiene, source package hygiene, PyInstaller check-only all green; exit code 0 |

Initial apply/verify (before native-review corrections) reached 1059 passed;
the native `gentle-ai review` lifecycle (see `apply-progress.md` → "Native
review corrections") found 1 CRITICAL and 6 non-blocking findings across 2
review lineages, all fixed except one deliberately-deferred performance
WARNING, adding 2 more tests (1061 total).

## Requirement verification

| Requirement | Evidence | Status |
|---|---|---|
| R1. Title/artist normalization for grouping | `tests/test_library_filter.py::test_normalize_title_strips_camelot_energy_suffix`, `::test_normalize_title_strips_single_digit_camelot_key`, `::test_normalize_title_strips_version_suffix`, `::test_normalize_title_strips_both_suffixes_regardless_of_order`, `::test_normalize_title_strips_repeated_version_suffixes`, `::test_normalize_title_preserves_remix_descriptor_content_but_strips_parens`, `::test_normalize_title_preserves_long_version_descriptor_content`, `::test_normalize_title_preserves_clean_descriptor_content`, `::test_normalize_title_groups_parenthesized_and_bare_remix_descriptor_forms` (CRITICAL regression — the exact three motivating screenshot titles), `::test_normalize_title_different_remix_descriptors_still_differ_after_paren_stripping` (negative control), `::test_normalize_title_does_not_falsely_strip_non_camelot_suffix`, `::test_normalize_title_strips_whitespace`, `::test_normalize_title_casefold_applied_after_suffix_stripping`, `::test_normalize_artist_casefolds_and_strips_whitespace`, `::test_normalize_artist_does_not_strip_suffixes` | PASS |
| R2. Blank/placeholder metadata never groups | `tests/test_library_filter.py::test_duplicate_group_key_none_when_title_none`, `::test_duplicate_group_key_none_when_artist_none`, `::test_duplicate_group_key_none_when_title_blank`, `::test_duplicate_group_key_none_when_artist_blank`, `::test_duplicate_group_key_none_when_title_is_placeholder_dash`, `::test_duplicate_group_key_none_when_artist_is_placeholder_dash`, `::test_duplicate_group_key_returns_normalized_tuple_for_valid_input`, `::test_suppressed_duplicate_paths_blank_metadata_rows_never_suppressed` | PASS |
| R3. Representative selection | `tests/test_library_filter.py::test_pick_representative_prefers_complete_status`, `::test_pick_representative_prefers_lower_missing_field_count_when_status_tied`, `::test_pick_representative_prefers_shorter_title_when_status_and_missing_tied`, `::test_pick_representative_uses_path_as_final_tiebreak`, `::test_suppressed_duplicate_paths_singleton_untouched`, `::test_suppressed_duplicate_paths_suppresses_all_but_representative`, `::test_suppressed_duplicate_paths_multiple_independent_groups`, `::test_suppressed_duplicate_paths_empty_input` | PASS |
| R4. Row-level composition with search (not the data layer) | `tests/test_library_screen.py::test_hide_duplicates_button_collapses_duplicate_rows`, `::test_hide_duplicates_button_off_shows_all_rows`, `::test_search_does_not_unhide_suppressed_duplicates`, `::test_duplicate_filter_only_considers_search_visible_rows` — the last test proves dedup only ever operates on rows `_apply_filter` already matched (narrowing search to `"v2"` leaves the v2 variant as a visible singleton, un-suppressed) | PASS |
| R5. UI toggle independence | `tests/test_library_screen.py::test_hide_duplicates_button_independent_of_status_mutual_exclusion`, `::test_hide_duplicates_toggle_does_not_uncheck_missing_filters`, `::test_clear_filters_includes_hide_duplicates_button`, `::test_restore_quick_filters_restores_hide_duplicates_button`, `::test_active_filter_count_includes_hide_duplicates_button` | PASS |
| R6. Duplicate-count visibility | `tests/test_library_screen.py::test_duplicate_count_label_empty_when_toggle_off`, `::test_duplicate_count_label_shows_count_when_enabled`, `::test_duplicate_count_label_empty_when_no_duplicates`, `::test_duplicate_count_label_clears_when_toggle_off_again` | PASS |

## Non-functional verification

- No existing Library screen tests broke: full pre-existing suites in
  `tests/test_library_filter.py`, `tests/test_library_screen.py`,
  `tests/test_library_screen_boundaries.py`, `tests/test_library_view_model.py`,
  and `tests/test_library_screen_preview.py` all still pass (78 total, 42 of
  which existed before this change).
- Each requirement above shipped with a RED-first regression test — confirmed
  failing before the corresponding production code existed (`ImportError` for
  the new `library_filter.py` functions; `AttributeError` for
  `hide_duplicates_button`/`duplicate_count_label` before the UI wiring — see
  `apply-progress.md` TDD Cycle Evidence table for exact pre-fix failures).
- Review budget: the four production-file diffs (`library_filter.py`,
  `library_screen_rendering.py`, `library_screen_builder.py`,
  `screens/library_screen.py`) are small, targeted additions well within the
  400-line review budget.

## Out of scope confirmation

- No changes to the recommendation/playlist-building engine.
- No mutation of scanned data, database rows, or files on disk — dedup is a
  pure row-hiding filter, confirmed by the row-level implementation in
  `_apply_duplicate_filter()` operating only on `QTableWidgetItem` display text
  and `setRowHidden`.
- `LibraryFilters` and `library_filter_state.py` left untouched, per design —
  confirmed by `git diff` showing no edits to either file.
- No persistence of the toggle's state across app restarts — `hide_duplicates_button`
  has no `QSettings`/persistence hook, matching every other quick-filter button.

## Known limitations (accepted, non-blocking, disclosed per native review)

- **Performance**: `_apply_duplicate_filter()` runs on every search keystroke
  (via `_apply_search_and_duplicate_filters()`) with no debounce, when Hide
  Duplicates is on. On very large libraries with an empty/broad search this is
  a real per-keystroke cost increase over search alone. Not fixed in this
  change — a proper fix needs new debounce infrastructure beyond this change's
  approved scope. Follow-up candidate for a future change.
- **False-positive grouping edge case**: stripping `(`/`)` as punctuation (the
  fix for the CRITICAL) means two titles sharing identical words modulo
  parentheses now normalize identically, even when the parenthetical text is
  part of the actual distinguishing title rather than a version/remix
  descriptor (e.g. `"Track One (B-Side)"` vs a genuinely different song
  `"Track One B-Side"` by the same artist). Accepted as an inherent tradeoff
  of the CRITICAL fix — display-only, fully reversible by unchecking the
  toggle, no data loss.
