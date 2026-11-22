# XfinAudio 2.30.0 Release Notes

Date: 2026-11-22

## Summary

2.30.0 is an **unreleased beta/source candidate** built on 2.29.1. It is the
first of three parts of one feature: the exporter can now **plan a set as a
Serato crate tree** — one parent crate with every track and one child crate per
`N` tracks — while the plan stays a dry run. **Nothing in the app uses it yet**,
and **every export behaves exactly as in 2.29.1**.

## The exporter plans a set as a crate tree

`plan_serato_crate_tree`, in `src/xfinaudio/exporting/serato_playlist_exporter.py`,
answers "what crates would this split write?" without writing anything. It
returns a `SeratoCrateTreePlan`:

- the **parent** crate holds every track of the set in the reviewed order;
- one **child** crate per segment holds that segment's tracks, in the same
  order, nested under the parent with Serato's own `%%` crate naming;
- each child is named `<n> (<first>-<last>)` with 1-based positions —
  `1 (1-5)`, `2 (6-10)`, `3 (11-15)` — and the last segment may be shorter, so
  twenty tracks split every five give `1 (1-5)`, `2 (6-10)`, `3 (11-15)` and
  `4 (16-20)`;
- the ancestors the parent needs, and which of them do not exist yet, come with
  the plan so a later export can create them exactly as it does today.

## The segment size is a real choice, and 2-50 is the whole range

A segment size below two is not a split, and above fifty it is a list rather
than a set, so the planner accepts `2`-`50` and refuses anything else — a float,
a boolean or a string included — with the same `ValueError` wording. A segment
size that covers the whole set is not a split either: with `N` equal to or
larger than the track count the plan holds **the parent only** and no child
crate. No split at all (`segment_size=None`) returns today's single-crate plan
unchanged.

## An automatic name picks one free number for the whole tree

An automatically named tree is named for the tree, not for its parent alone: the
planner looks for the first number free for the parent **and** every child it
will write, so an existing older export takes `(2)`, `(3)` and the new tree
lands beside it instead of inside it. A number still held by a leftover child
crate counts as taken, so a new export never adopts crates it did not write. A
typed or saved name keeps today's exact-name semantics, and its children follow
that name.

## What does not change

- **Exports are unchanged.** The confirmed Serato export still writes one crate
  per confirmation — same destination detection, same preview, same native
  confirmation, same receipt, same rollback.
- **Nothing on screen changes.** The plan is not wired to the export path, the
  options screen, the IPC surface or the receipt in this version.
- The export boundaries stay as they were: no live Serato database V2 file is
  written, and metadata scanning stays read-only.
- No audio file is mutated outside loudness tag writing.

## What comes next

- **2.31.0** adds the export that writes a split: confirmation covers the whole
  tree, and a failed crate removes everything that export created.
- **2.32.0** puts «Dividir en tramos» on the export options screen.

## Known limitations

- The planner is library code with no caller in the app, so a DJ cannot ask for
  a split yet.
- The 2.30.0 candidate is source-only: no installer, updater or binary
  redistribution is claimed by this version.
