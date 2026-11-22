# XfinAudio 2.25.0 Release Notes

Date: 2026-11-22

## Summary

2.25.0 is an **unreleased beta/source candidate** built on 2.24.0. **A list that
holds the same track twice can be reordered**, the review warnings are in
Spanish, `kill` and Ctrl+C close the app in order, and the desktop documents
describe the current Serato export.

## Reordering a list with a repeated track

A saved playlist opened as the list in progress can hold the same track twice.
It could already be edited but not reordered: **Subir**, **Bajar** and **Mover**
acted on the first copy of the track instead of the row that was chosen.

Each move now acts on the selected row, and every other track keeps its place.
An order that drops one copy of a repeated track is now **refused** instead of
accepted.

## Review warnings in Spanish

The optimizer and the candidate pool reported some warnings in English:

- no possible list for the requested length or controls;
- the search stopped without a full list;
- incomplete opening, closing or manual tracks were ignored.

They appear in Spanish now, like the rest of the review.

## Closing with a signal

`kill` (SIGTERM) and Ctrl+C (SIGINT) close the app with the orderly shutdown:
the core is drained and the Serato and offline writes are committed. The
«Cambios sin guardar» dialog does not appear, even when there are unsaved
drafts; those drafts are discarded, and the list in progress is still there on
the next start.

## Current Serato export in the documents

The desktop source guide and the manual QA checklist described the old export.
They now describe the current one: automatic Serato folder, export in two steps,
unique crate names, and blocked while Serato is open.

## What does not change

- The assistant's single-track move still names tracks by id, so it is refused
  for a repeated track and reports it as stale; the full assistant reorder works.
- Saving, exporting to Serato and editing a list behave as in 2.24.0.
- The other warnings of the review keep their wording.

## Known limitations

- A repeated track is only distinguishable by its row, so the assistant cannot
  address one of its copies on its own.
