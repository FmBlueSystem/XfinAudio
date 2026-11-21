# XfinAudio 2.16.0 Release Notes

Date: 2026-11-20

## Summary

2.16.0 is an **unreleased beta/source candidate** built on 2.15.0. Generated
lists now reach the size that was asked for much more often, with better
transitions, and generating no longer fails when another program rewrote the
tags of library files.

## Lists reach the requested size

**Without an opening track.** The engine used to pick its candidates spread by
energy and in folder order, without looking at tempo; most were then discarded
because they could not be chained by BPM. It now takes the candidates from the
densest tempo neighbourhood of the library (or of the period or genre asked
for).

**With a genre.** The safe and balanced alternatives used to keep only the
tracks of that genre that happened to be among 150 pre-selected candidates.
They now choose from every track of the genre in the library.

Measured on a library of 10 391 tracks, 20 tracks requested, balanced
alternative:

| Request | Before | Now |
|---|---|---|
| No options | 5 tracks, score 0.53 | 20 tracks, score 0.69 |
| Period 1980–1989 | 8 tracks, 0.43 | 20 tracks, 0.72 |
| Period 1990–1999 | 6 tracks, 0.46 | 20 tracks, 0.72 |
| Genre «Synth Pop & New Wave» | 1 track | 20 tracks, 0.73 |
| Genre «House & Electronic» | 3 tracks, 0.40 | 20 tracks, 0.77 |
| Opening track + genre «Synth Pop & New Wave» | 4 tracks, 0.77 | 20 tracks, 0.83 |

A request the library cannot satisfy still comes out short, with the short-list
notice and its fixes: an opening track at 98 BPM with a genre that has no track
near that tempo gives one track.

## Extending repairs weak stretches

When a list is extended, a new track now goes between two tracks that mix
badly, when it mixes well with both, before tracks are added at the end.

## Generating after another program rewrote tags

A DJ program that rewrites the tags of the files it plays changes their size and
date. Generating a list that included such a file failed with «prepare a current
review». Generating and choosing an alternative now accept a file that is still
the same recording (same place, readable, same length). A file that is missing,
moved, unreadable or of another length still cannot enter a list.

## Compatibility

No stored data changes. A generation with an opening, closing or required track
and no genre gives the same candidates as before.

## Known limitations

- Scores of a full list are typically 0.69 to 0.83; some transitions below 50 %
  can remain and show as «Débil» in the review.
- Measured on one library copy without the app window.
