# XfinAudio 2.14.0 Release Notes

Date: 2026-11-15

## Summary

2.14.0 is an **unreleased beta/source candidate** built on 2.13.0. Editing a
generated list and talking to the list assistant are much faster on a large
library. Nothing else changes.

## Why it was slow

Every review edit and every assistant message re-checked every file of the
library on disk, several times per operation, to be sure no file had changed.
On a library of 10 000 tracks on an external drive, one replacement took 17 to
32 seconds and applying a change from the assistant took about a minute.

## What changed

- The library is read once per operation (plus one final check) instead of five
  to seven times.
- The on-disk check is made only for the tracks that matter: the tracks in the
  list, the tracks of an undo or redo step, and a track that is about to enter
  the list. Every other track is used from the library record.

Measured on a copy of a library of 10 391 tracks on an external drive:

| Operation | Before | Now |
|---|---|---|
| Compare a replacement | 17–32 s | 2.2 s |
| Prepare an assistant message | 9–13 s | 3.0 s |
| Load the review evidence | 6.7 s | 1.1 s |
| Start the local service with a list in progress | 9.2 s | 3.9 s |
| Extend a list by 3 tracks | — | 2.8 s |

## What stays protected

A track of the list that was changed, moved or deleted on disk since the list
was generated still stops the edit, the assistant message, the save and the
export, exactly as before. A track that changed on disk cannot enter the list.

One difference: a track outside the list that changed on disk no longer blocks
an edit that does not use it. If the engine picks such a track as a replacement,
the edit is refused and asks for a new review, where before the track was
skipped silently.

## Compatibility

No stored data changes.

## Known limitations

- Generating a list and scanning the library are as fast or slow as before.
- Times were measured on one library copy without the app window.
