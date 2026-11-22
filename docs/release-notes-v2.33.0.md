# XfinAudio 2.33.0 Release Notes

Date: 2026-11-22

## Summary

2.33.0 is an **unreleased beta/source candidate** built on 2.32.0. It is the
first of three parts of one feature: **every crate XfinAudio writes to Serato now
lives under the `XfinAudio` parent crate**. A saved playlist exported with a quick
export or from the options screen, and a name typed on the options screen, are
written as `XfinAudio › <name>` (`XfinAudio%%<name>.crate`) instead of at the
Serato root. Generated lists and metadata worklists keep today's names, which
already sit under `XfinAudio`.

## A saved playlist and a typed name land under XfinAudio

- A **saved playlist** exported with **Exportar a Serato** from its card, and the
  same playlist renamed on **Opciones de exportación**, are written under the one
  parent crate: the playlist «22 nov» becomes **XfinAudio › 22 nov**, the file
  `XfinAudio%%22 nov.crate`.
- A **name typed** on **Opciones de exportación** — for a reviewed set or for a
  metadata worklist — is nested the same way, and the name itself is still used
  exactly as typed inside the parent.
- The preview and the native confirmation name that crate, so the DJ approves the
  nested name and the parent the export creates in one dialog. The receipt names
  the nested crate and the parent that was created, and **Mostrar crate
  exportado** reveals it.

## A split tree nests under the same parent

With **Dividir en tramos** the whole tree moves under `XfinAudio`: a saved or
typed name becomes the tree's parent, so «22 nov» with **Cada 5 pistas** writes
**XfinAudio › 22 nov** with **1 (1-5)**, **2 (6-10)** and so on indented under it
(`XfinAudio%%22 nov%%1 (1-5).crate`). The preview, the confirmation, the receipt
and the rollback cover the whole tree exactly as they did in 2.32.0.

## Generated lists and metadata worklists keep their names

An automatic name was already nested, and it still is: a generated set keeps
**XfinAudio › Harmonic Journey 14-nov**, with **(2)** and **(3)** when that name
already exists, and a metadata worklist keeps
**XfinAudio › Metadata › <status> <count>-<date>**. Their bytes, their parents and
their suffixes are unchanged by this version.

## The parent is created empty and never rewritten

When `XfinAudio.crate` is missing, the same confirmed export creates it with **no
tracks**, and it is reported as a parent to create in the preview and as created
in the receipt. An `XfinAudio` crate that already exists is **never rewritten,
replaced or backed up**: only the crate of that export is written.

## The prefix is never doubled

A name that already begins with `XfinAudio%%` is kept exactly as it is, so
`XfinAudio%%Reparación de BPM` stays that file instead of becoming
`XfinAudio%%XfinAudio%%Reparación de BPM`. Case variants of the parent name are
recognised the same way, so a typed name never produces a second parent level.

## Re-exporting replaces its own crate, with a backup

Exporting the same saved playlist again targets `XfinAudio › <name>` as an exact
name: the preview says it will be **replaced**, the confirmation approves that,
and the write keeps a `.bak` copy of the crate it replaced — the same behaviour a
typed name already had at the Serato root.

## Crates already at the Serato root are never touched

A crate the DJ keeps at the Serato root — an earlier «22 nov», an earlier
`XfinAudio` crate, anything else — is **never moved, renamed, replaced or
deleted**. The export writes its own nested crate beside it and leaves the root
file byte-identical, with no backup beside it.

## The typed-name cap counts the prefix

The desktop shell's typed-name check now measures the file the core really
writes: `<name>.crate` becomes `XfinAudio%%<name>.crate`, so the 240-byte file-name
limit counts those 11 extra bytes. A name that already carries the prefix is not
doubled and keeps the whole budget. A name that only fitted the root file is now
refused at the boundary with **Invalid crate name**, before anything is planned.

## Documentation and QA follow the change

The Serato section of `desktop-electron/README.md` describes the parent crate,
the nested saved and typed names, the never-doubled prefix and the untouched root
crates. QA step 5 of `desktop-electron/QA_SERATO_V4.md` checks the same by hand:
a saved and a typed name under `XfinAudio`, an existing parent that is not
rewritten, a pre-existing root crate of the same name that stays identical with
no backup, and a typed name with the prefix that is not doubled — always on a
disposable fixture, never on a real `_Serato_` folder.

## What does not change

- **A generated export is unchanged**: the same automatic names, the same `(2)`
  and `(3)` suffixes, and the same parents.
- **The export flow is unchanged**: same detection, same read-only preview, same
  native confirmation, same receipt, same rollback, and nothing written before
  the confirmation.
- The export boundaries stay as they were: no live Serato database V2 file is
  written, no audio file is mutated outside loudness tag writing, and no path,
  destination or confirmation flag crosses the bridge.

## What comes next

- **2.34.0** opens **Opciones de exportación** directly, from the review screen
  and from each saved playlist card.
- **2.35.0** checks the source tracks once for a whole tree instead of before
  every crate, so a tree export stops being slow.

## Checked live with Serato DJ Pro 5.1

The two Serato behaviours this feature depends on were checked live on
2026-11-22 with Serato DJ Pro 5.1: a split tree appeared in Serato with its
parent and its children, the parent showed its own 20 tracks without duplicating
the children's, each child showed its segment, and the same track in the parent
and in a child displayed the same.

## Known limitations

- The change moves where new exports land. Crates from earlier versions stay
  where they were, at the Serato root, and the DJ can delete them from Serato by
  hand whenever they no longer need them; XfinAudio never moves or removes them.
- The app still refuses to commit a crate while Serato DJ Pro or Serato DJ Lite
  is running, because Serato rewrites its crates when it quits.
- The 2.33.0 candidate is source-only: no installer, updater or binary
  redistribution is claimed by this version.
