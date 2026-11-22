# XfinAudio 2.35.0 Release Notes

Date: 2026-11-22

## Summary

2.35.0 is an **unreleased beta/source candidate** built on 2.34.0. It is the
third and last part of one feature, and it is a **speed change with no change in
outcome**: a confirmed Serato export now verifies its source tracks **once per
commit** instead of on every write guard, so **29 full source reloads became 1**
for a five-crate tree and **9 became 1** for a single crate.

## Why it was slow

Every crate write ran the same guard, and that guard reloaded and re-verified the
whole export source each time: it re-read every scanned track and re-checked the
destination. A five-crate tree paid that cost 29 times and a single crate paid it
9 times; a five-crate tree took about **30 s** on the external drive in the live
check of 2026-11-22.

## One verification per confirmed export

The confirmed commit now verifies the source and every planned target **once**,
before its first write, and keeps that binding. Each later write guard compares
the **track identities already collected** by that verification instead of
reloading anything, so the work no longer grows with the number of crates.

## The identities are the same ones as before

The comparison uses the identity tuple `load_source` already recorded: the
lineage of the track's parent folders, its device, inode, size, modification time
and change time. A scanned track that is **deleted, replaced, renamed, rewritten
or turned into a symlink** between two crates of the same commit is therefore
still detected, and the export is refused with the same **stale-source** outcome
as before: the whole tree rolls back and nothing of it survives.

## Every safety rule stays

- The **Serato-running** refusal is unchanged.
- The **destination lineage** is re-checked on every write, and the **per-crate
  target identity** and backup check are unchanged, so nothing that appeared or
  changed in the destination can impersonate the preview.
- The **stale-preview** refusal still applies to every crate of the tree.
- The **caps** — 500 track references and 16 MiB per crate — are unchanged.
- A failure anywhere still triggers the **all-or-nothing rollback**, including the
  parent crates the export created.
- The core serialises one command at a time, so no selector or catalogue edit can
  land between two crates of the same commit.

## Outcomes are byte-identical

The same crates, the same parent crates, the same bytes, the same backups, the
same receipt and the same rollback as in 2.34.0. Only the number of full source
reloads changed.

## The typed-name pre-check counts the prefix

The export screen's name length check now measures the crate file the core really
writes — `XfinAudio%%<name>.crate` — exactly as the desktop shell's IPC check
already did, and a name that carries the prefix is not doubled. A name that only
fitted the bare `<name>.crate` file is refused while it is typed, before a preview
is prepared.

## What does not change

- **The export flow is unchanged**: same detection, same read-only preview, same
  native confirmation, same **Dividir en tramos** control, same receipt, and
  nothing written before the confirmation.
- **A quick export is unchanged**: one click from the review screen or a saved
  playlist card still writes exactly one crate.
- The export boundaries stay as they were: no live Serato database V2 file is
  written, no audio file is mutated outside loudness tag writing, and no path,
  destination or confirmation flag crosses the bridge.

## Known limitations

- This version reports the change in **reload counts** (29 → 1 for a five-crate
  tree, 9 → 1 for a single crate), not in measured seconds: the live timing on the
  external drive is to be measured after release, and it needs Serato DJ closed
  because a confirmed export refuses to run while Serato is open.
- The export still refuses to commit while Serato DJ Pro or Serato DJ Lite is
  running, because Serato rewrites its crates when it quits.
- The 2.35.0 candidate is source-only: no installer, updater or binary
  redistribution is claimed by this version.
