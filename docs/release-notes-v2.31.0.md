# XfinAudio 2.31.0 Release Notes

Date: 2026-11-22

## Summary

2.31.0 is an **unreleased beta/source candidate** built on 2.30.0. It is the
second of three parts of one feature: the local core can now **export a set as a
Serato crate tree** — one parent crate with every track and one child crate per
`N` tracks — with a single confirmation and all-or-nothing behaviour. The planner
shipped in 2.30.0 is now a real export path. **No screen sends a split yet**, so
the option the DJ will use arrives in 2.32.0, and **an export without a split
behaves exactly as in 2.30.0**.

## The split preview lists every crate of the tree

`serato.preview` in `src/xfinaudio/headless/serato_export.py` accepts an optional
`segmentSize`: an integer of `2` to `50` tracks, refused — with `invalid_params`
and the same wording as the planner — when it is a float, a boolean, a string or
out of that range, and refused for a metadata worklist export, which stays a
worklist rather than a set. A preview that carries a segment size answers with a
`crates` list, parent first: each entry names the crate file, its track count and
its `action`, `create` or `replace`, so the confirmation can say what the export
will write and what it will overwrite before anything is touched.

## Every crate of the tree passes the same checks

The parent and every child go through the checks a single crate already passed:
the 16 MiB byte limit, the 500 track-reference limit, name validation, target
containment inside the destination folder, the same-volume rule, payload
validation of the crate bytes, and the round-trip validation of what was
actually written. A tree is not weaker than one crate, and a failure in any crate
fails the export instead of writing the rest.

## One confirmation writes the tree, all or nothing

A confirmed commit keeps the guard the app already had — the export is refused
while Serato DJ is running, with the same message — and then writes in one
destination pass: the ancestors the parent needs, the parent with every track in
the reviewed order, and each child in order. If any crate fails to write or to
validate, **the whole tree is undone in reverse**: every crate this export wrote
is removed, a crate it replaced is restored from its backup, and every ancestor
it created is removed again with its descendants. A crate that cannot be
restored is kept and logged, and the export still reports the failure instead of
claiming a success the folder does not show.

A crate that changed after the preview keeps the existing stale-preview refusal:
the tree is re-checked per crate against what the preview bound, so a child
edited behind the app's back stops the export before it writes anything.

## The receipt names every crate

The receipt keeps the parent crate as `filename`, so «Mostrar en Finder» and the
receipt path resolve exactly as before, and adds `files` with every crate the
export wrote and its track count. `trackCount` stays the parent's count, and
`validated` and `backupCreated` are true only when every crate agrees. Replaying
the same confirmation returns that same receipt and writes nothing.

## What does not change

- **An export without a split is unchanged**: no `crates` in the preview, no
  `files` in the receipt, and the same crate bytes, the same parents, the same
  receipt and the same rollback as in 2.30.0.
- **Nothing on screen changes.** No screen sends `segmentSize` yet, so the export
  available to a DJ today is still the single crate of the review screen, the
  saved-playlist card and quick export.
- The export boundaries stay as they were: no live Serato database V2 file is
  written, no audio file is mutated outside loudness tag writing, and the
  machine's own `_Serato_` folder is only written when the DJ picked it as the
  destination.

## What comes next

- **2.32.0** puts «Dividir en tramos» on the export options screen, lists the
  tree in the preview and the confirmation, and reveals the parent crate from the
  receipt.

## Known limitations

- A crate that the export replaced and then rolled back is restored, but the
  `.bak` file that the write left beside it is kept rather than removed. This is
  the behaviour a single-crate rollback already had.
- Two Serato behaviours are still unverified against a real Serato DJ: whether a
  parent crate shows the tracks of its own children, and how Serato shows the
  same track in both the parent and a child. The export writes what the DJ asked
  for; the confirmation wording will follow what live Serato proves in 2.32.0.
- The 2.31.0 candidate is source-only: no installer, updater or binary
  redistribution is claimed by this version.
