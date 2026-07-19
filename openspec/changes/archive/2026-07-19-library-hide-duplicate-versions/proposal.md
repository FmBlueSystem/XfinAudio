# Proposal: Hide Duplicate Track Versions in the Library Screen

## Intent

The Library table shows multiple rows for what is really the same song when several near-duplicate files exist on disk (e.g. three files for "Right On Track (Kwikmix By Dj Richie Rich)" with slightly different titles). Add a "Hide Duplicates" quick-filter toggle that collapses each such group down to one representative row. Locked via `/grill-me-codex` (see `PLAN.md` / `PLAN-REVIEW-LOG.md` at repo root for the full grill + 5-round adversarial-review transcript).

## Scope

### In scope

- Pure grouping/normalization functions in `src/xfinaudio/desktop/library_filter.py`.
- A new row-level filtering pass in `src/xfinaudio/desktop/library_screen_rendering.py`, composed correctly with the existing live-search row-hiding mechanism.
- A new "Hide Duplicates" quick-filter button plus a duplicate-count label in `src/xfinaudio/desktop/library_screen_builder.py`.
- Accessibility/tooltip/tab-order wiring for the new button in `src/xfinaudio/desktop/screens/library_screen.py`.

### Out of scope

- Recommendation/playlist-building engine changes (a generated playlist can still include multiple versions of the same song — flagged as a separate future change, not addressed here).
- Any mutation of the underlying scanned data, database rows, or files on disk.
- Persisting the toggle's state across app restarts.
- A configurable/user-editable suffix-pattern list.

## Success criteria

1. Given 2+ tracks with the same artist and a title differing only by app-generated technical suffixes (`" - <key> - Energy <N>"`, `"(vN)"`), enabling "Hide Duplicates" shows only one representative row per group.
2. Genuinely different remixes/edits of the same base song (e.g. "Billie Jean (kwikMIX by DJ Volume)" vs "Billie Jean (Long Version)") are never grouped together.
3. Typing a search query that matches only a duplicate-suppressed row still finds it correctly (dedup composes with search, never permanently hides a search match).
4. Tracks with blank/missing title or artist are never grouped with each other.
5. The representative chosen per group is the one with the most complete metadata; ties break on shortest title, then path.
6. A label shows how many duplicate rows are currently hidden.
7. All verification commands pass.
8. No audio files are mutated; no live Serato database V2 writes.

## Rollback plan

Isolated, additive change (new functions + one new UI control); revert by removing the button wiring and the new row-level filter pass if a regression surfaces.

## Review budget

Estimated changed lines: ~120 production + ~150 test lines, within the 400-line budget.
