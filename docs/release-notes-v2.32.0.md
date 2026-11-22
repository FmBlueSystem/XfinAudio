# XfinAudio 2.32.0 Release Notes

Date: 2026-11-22

## Summary

2.32.0 is an **unreleased beta/source candidate** built on 2.31.0. It is the
third and last part of one feature: **«Dividir en tramos»** on the export
options screen lets the DJ export a set as a **Serato crate tree** — one parent
crate with every track and one child crate per `N` tracks — with one confirmation
and all-or-nothing behaviour. A one-click quick export still writes a single
crate, and an export without a split is unchanged.

## The options screen offers the split, for that export only

**Opciones de exportación** now offers **Dividir en tramos**:

- **No dividir** is the default and writes today's single crate.
- **Cada N pistas** writes the parent with every track plus one child crate per
  segment. **N** is a whole number from `2` to `50`, `5` by default, typed in a
  **Pistas por tramo** field that marks anything outside that range as invalid
  instead of rounding it. The field is disabled while **No dividir** is chosen.
- The choice belongs to **that export only**. It is never remembered, and
  opening another set starts on **No dividir** again.
- A metadata worklist keeps its own naming, so the split is disabled for it —
  the core refuses a segment size there.

The help text beside the control states the same thing in Spanish, and the
control is unavailable while the export itself is blocked.

## The preview and the confirmation list every crate

With a split, the preview lists the tree, parent first and its children indented
under it, each with its track count and whether it is **created** or
**replaced**: «Se escribirán 5 crates:» followed by one line per crate. The
native confirmation shows the same crates with the same counts and actions, so
the DJ approves the whole tree in one dialog. Nothing is written before that
confirmation, and the Serato-running refusal keeps its own Spanish wording.

## The receipt names the tree and Mostrar opens the parent

After a split the status reads **«Árbol exportado a Serato: N crates»**, the
receipt names every crate written with its track count, and **«Mostrar crate
exportado»** opens the **parent** crate file — the parent stays the receipt's
`filename`, so the Finder reveal resolves exactly as it did for a single crate.
A single-crate export keeps its «Crate exportado y validado: <file>» wording.

## The IPC surface accepts one shape of split

The desktop shell accepts `segmentSize` on the Serato preview only as a **whole
number from 2 to 50**; a float, a string, an explicit `null`, a boolean or an
out-of-range value is refused before it reaches the core. A preview without a
split sends no `segmentSize` field at all, so today's request is byte-for-byte
what it was. A quick export — one click from the review screen or from a saved
playlist card — never sends a size and keeps writing the single crate.

## Documentation and QA follow the feature

The Serato section of `desktop-electron/README.md` describes the tree, the
caps that now apply per crate, and the one-click behaviour, and
`desktop-electron/QA_SERATO_V4.md` gains step 17: check the control and its
defaults, prepare a split preview and confirm it writes nothing, confirm the
whole tree, read the receipt, repeat a one-click export to see the single crate,
and record the live Serato checks on a disposable fixture.

## What does not change

- **An export without a split is unchanged**: same preview, same confirmation,
  same bytes, same receipt, same rollback.
- **Quick export is unchanged**: one click from the review screen or a saved
  playlist card still writes exactly one crate.
- The export boundaries stay as they were: no live Serato database V2 file is
  written, no audio file is mutated outside loudness tag writing, and no path,
  destination or confirmation flag crosses the bridge.
- Metadata scanning stays read-only, and the 500-reference and 16 MiB caps apply
  to every crate of a split as they did to a single crate.

## Known limitations

- Two Serato behaviours are still unverified against a real Serato DJ: whether a
  parent crate shows the tracks of its own children, and how Serato shows the
  same track in both the parent and a child. The export writes what the DJ asked
  for; QA step 17 records what live Serato does on a disposable fixture, never on
  a real `_Serato_` folder.
- Cutting a set by energy phases — the phases of the recommended arc — is a
  later stage; this version splits by a fixed number of tracks only.
- The app still refuses to commit a crate while Serato DJ is running, because
  Serato rewrites its crates when it quits.
- The 2.32.0 candidate is source-only: no installer, updater or binary
  redistribution is claimed by this version.
