# XfinAudio 2.24.0 Release Notes

Date: 2026-11-22

## Summary

2.24.0 is an **unreleased beta/source candidate** built on 2.23.0. **Generating
a list is about three times faster** on a large library, and fails less often
with «La biblioteca cambió».

## Faster generation

Before preparing a list the app confirms that every audio file is still the
recording it scanned. One generation did that over the **whole library five
times**; it took about 90 % of the time and did not depend on how many tracks
were asked for.

Now one generation reads the whole library **once**, and its final check
re-reads only the tracks of the lists it produced.

Measured on a 10 391-track library on an external drive:

| | Before | Now |
| --- | --- | --- |
| Generate 20 tracks, in the app | 47-53 s | 13-16 s |
| Generate 20 tracks, core only | 41-60 s | 18 s |
| «Finalizando la preparación» step | 32-38 s | under 3 s |
| Choose another variant, core only | not measured | 2 s |

A shorter generation also leaves less time for a file to change in the middle,
which is what made a first attempt fail with «La biblioteca cambió».

## What does not change

- A file that is missing, moved, unreadable or a different recording still
  enters no list.
- A track of the produced lists that is deleted or replaced during the
  generation still fails it.
- Saving, exporting to Serato and editing a list verify their tracks as before.

A change to a library track that is in none of the produced lists no longer
fails the generation.

## Known limitations

- The remaining time is mostly the one whole-library read. Files whose size or
  date differ from the last scan have their tags read again on every
  generation; scanning the library again removes that part.
