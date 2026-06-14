# Proposal: Auto-hide Missing Column in Library Screen

## Intent

Give the DJ more horizontal screen space by hiding the "Missing" metadata column by default, and let them reveal it on demand with a toggle button.

## Scope

### In scope

- Hide the "Missing" column in the Library screen track table by default.
- Add a toggle button to show/hide the column.
- Persist the visible/hidden state across the current session only (no settings file changes).

### Out of scope

- Changes to other tables (Review, Export, Metadata Worklist).
- Persistence across app restarts.
- Renaming or repositioning the column.

## Motivation

The Library table has many columns (Title, Artist, BPM, Key, Energy, Duration, Color, Missing, Genre, Status, Preview, Path). On smaller MacBook screens the table feels cramped. The Missing column is only useful during metadata cleanup, not while browsing or building playlists, so it is a good candidate for autohide.

## Success criteria

1. The Missing column is hidden when the Library screen first appears.
2. A toggle button shows/hides the Missing column.
3. Existing row selection, sorting, filtering, and spectral color updates continue to work when the column is hidden or shown.
4. All verification commands pass.
5. No audio files are mutated.

## Rollback plan

- Remove the toggle button and restore the Missing column to visible by default.

## Review budget

Estimated changed lines: ~40 production + ~30 test lines, within the 400-line budget.
