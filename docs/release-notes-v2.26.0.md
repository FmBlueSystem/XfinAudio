# XfinAudio 2.26.0 Release Notes

Date: 2026-11-22

## Summary

2.26.0 is an **unreleased beta/source candidate** built on 2.25.0. **The list in
progress is recovered after new analysis and kept while its files are out of
reach**, and **preparing an assistant turn reads the list's tracks instead of the
whole library**, so a slow external drive no longer restarts the core.

## The list in progress comes back after new analysis

A saved list in progress was dropped at start as soon as one of its tracks
differed from the stored record. Completing spectral, danceability, edge,
loudness or tonal analysis rewrote those records, so the list disappeared even
though every file was intact. One list was lost this way on 2026-11-20.

Tracks that only gained or changed analysis data are now accepted, and the list
is recovered on screen with the fresh records.

## The list is kept when its files are not reachable

When the music drive is not mounted at start, the stored list is **no longer
deleted**: it is reported as not recoverable for that start and recovered on a
later start once the drive is ready again.

A file that is really gone keeps today's behavior: while the drive is mounted
and the track is missing, or when a track is a different recording, the list is
dropped and the store is cleared.

## Preparing an assistant turn stays bounded

Preparing a chat turn checked every library file on disk and read the library
three times. On a 10,000-track external drive it passed the fixed 120 s request
deadline and the core was killed and restarted.

A prepared turn now checks on disk only the tracks of the list in progress and
the tracks the request names, and reads the library once per command. On a
200-track test library the same request went from 240 disk checks to 50 and from
3 library reads to 1. Tracks outside the list keep their stored record and
identity. This bounded check belongs to the assistant turn (preparing it, the
confirmation it re-checks and the run itself); no other command uses it.

`ai.prepare` is no longer killed by the fixed 120 s request deadline, the same
treatment `ai.run` already had, so slow disk I/O is not reported as a hang and
does not restart the core.

## What does not change

- Staleness protections stay: a list track changed on disk still makes a
  prepared chat turn stale.
- Extending, replacing, inserting and every review edit still check the unlisted
  library files on disk exactly as before, so a deleted library track leaves the
  candidate pool and the answer the same way it always did.
- Generation and export guards still check every track they checked before.
- Every other path that clears the store (scan, generate, select, completed
  profiles, a loudness run, a settings update, a cancelled preparation, opening
  a saved playlist) is unchanged.
- Saving, exporting to Serato and editing a list behave as in 2.25.0.

## Known limitations

- A repeated track is still only distinguishable by its row, so the assistant's
  single-track move cannot address one of its copies on its own; the full
  assistant reorder works. This is unchanged from 2.25.0.
