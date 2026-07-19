# Specification: Hide Duplicate Track Versions in the Library Screen

## Requirements

### R1. Title/artist normalization for grouping

**GIVEN** a track title containing an app-generated technical suffix (`" - 12A - Energy 7"`, `"(v2)"`, or both in either order)
**WHEN** `_normalize_title_for_grouping` processes it
**THEN** all such suffixes are stripped (repeatedly, until none remain), and the result is casefolded.

**GIVEN** a title containing a remix/edit/mix descriptor in parentheses (e.g. `"(kwikMIX by DJ Richie Rich)"`, `"(Long Version)"`, `"(Clean)"`)
**THEN** that descriptor is preserved verbatim — never stripped.

**GIVEN** an artist name with mixed case or leading/trailing whitespace
**WHEN** `_normalize_artist_for_grouping` processes it
**THEN** it returns `artist.strip().casefold()` — no suffix stripping.

### R2. Blank/placeholder metadata never groups

**GIVEN** a track with `None`, blank, or (at the row-level, post-render) the `"—"` placeholder for title or artist
**WHEN** `_duplicate_group_key` evaluates it
**THEN** it returns `None`, meaning the track is always treated as a singleton and never grouped with another blank-metadata track.

### R3. Representative selection

**GIVEN** 2+ tracks sharing a duplicate group key
**WHEN** `_pick_duplicate_representative` selects the representative
**THEN** it picks by, in order: (1) `status == "complete"` over anything else, (2) lower `missing_field_count`, (3) shortest original (non-normalized) title, (4) alphabetical `path` as the final deterministic tiebreak.

### R4. Row-level composition with search (not the data layer)

**GIVEN** the Library screen's live search operates entirely via row-hiding on already-rendered rows (`_apply_filter`), not through `LibraryFilters`/`tracks_for_display`
**WHEN** "Hide Duplicates" is enabled
**THEN** duplicate suppression runs as a row-level pass (`_apply_duplicate_filter`) that only considers rows already visible after search, so it can never permanently hide a row a search query would otherwise match.

**GIVEN** the user types into the search box while "Hide Duplicates" is checked
**WHEN** `_on_search_changed` fires
**THEN** both the search pass and the duplicate-suppression pass run together (via one composite `_apply_search_and_duplicate_filters` method), not just the search pass alone — so previously-suppressed duplicates never reappear mid-typing.

### R5. UI toggle independence

**GIVEN** the existing quick-filter buttons (`Complete`/`Incomplete`/`Missing BPM`/`Missing Key`/`Missing Energy`) are mutually exclusive within two groups
**WHEN** "Hide Duplicates" is toggled
**THEN** it does not affect, and is not affected by, any of those buttons' checked state — it is wired independently, not added to the `quick_filter_buttons` mutual-exclusion tuple.

**GIVEN** "Clear Filters" is clicked, or an undo restores a prior filter selection
**THEN** the "Hide Duplicates" button's checked state is included consistently, the same as every other quick-filter button.

### R6. Duplicate-count visibility

**GIVEN** "Hide Duplicates" is enabled and N rows are currently suppressed
**THEN** a label shows "N duplicates hidden" (or is empty/hidden when N is 0 or the toggle is off).

## Non-functional

- The change must not break existing Library screen tests.
- Each requirement above ships with a RED-first regression test (strict TDD).
- The change must stay within the 400-line review budget.
