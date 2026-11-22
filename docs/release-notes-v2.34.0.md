# XfinAudio 2.34.0 Release Notes

Date: 2026-11-22

## Summary

2.34.0 is an **unreleased beta/source candidate** built on 2.33.0. It is the
second of three parts of one feature: **«Opciones de exportación»** — the screen
that holds **Dividir en tramos** — can be opened directly, from the review screen
and from each saved playlist card. Until now it was only reachable from the
notice that a quick export leaves behind, a detour the live check found on
2026-11-22.

## The review screen opens the export options next to «Exportar a Serato»

A secondary button, **«Opciones de exportación»**, sits right after the primary
**«Exportar a Serato»** button on the review screen and is styled as a secondary
action, so the primary action stays the one-click export. Clicking it opens the
export options screen for the reviewed selection, and it starts **no export**:
the screen is opened, its own destination detection runs, and nothing is written
until the DJ prepares a preview and confirms.

It answers to the same gates as the export button beside it: it is disabled while
an operation is running, while the core is unavailable, and whenever the review
carries no source the app could export — a review with no `reviewId` and no saved
playlist. A review that can export can therefore always open its options.

## Every saved playlist card opens them too

Each saved playlist card gains **«Opciones de exportación»** in its actions row,
directly after **«Exportar a Serato»** and before **Editar**, **Renombrar** and
**Duplicar**, which keep their positions and order. The button is secondary
styled and names its playlist, so a screen reader announces **«Opciones de
exportación: <name>»**. The click opens the export options screen for that saved
playlist and starts no export; like the other card actions, it is disabled while
an operation runs.

## Same source, same name, same gating as the quick export

Both new buttons start from the **same request** the quick export builds, so the
options screen receives exactly what a one-click export would have sent:

- an **opened saved list** keeps its playlist id — sent as the decimal string the
  shell accepts — and its saved name, which arrives in the name field;
- a **generated list** keeps its review and leaves the name empty, so the core
  proposes the automatic short name during the preview, as it does for a quick
  export.

The options screen then shows the same source line it always showed — «Origen:
selección revisada actual» or the saved-playlist variant — with the same name and
the same **Dividir en tramos** control. Nothing about the screen itself changed.

## Quick export is unchanged

**«Exportar a Serato»** on the review screen and on a saved playlist card still
starts one quick export and stays on the page: no navigation, the same request,
the same receipt or the same cancelled notice. The notice a quick export leaves
still offers its own **«Opciones de exportación»** button, so the earlier route
keeps working beside the new ones.

## What does not change

- **The export flow is unchanged**: same detection, same read-only preview, same
  native confirmation, same receipt, same rollback, and nothing written before
  the confirmation.
- **The export options screen is unchanged**: its fields, its **Dividir en
  tramos** control, its preview and its confirmation behave as in 2.33.0.
- The export boundaries stay as they were: no live Serato database V2 file is
  written, no audio file is mutated outside loudness tag writing, and no path,
  destination or confirmation flag crosses the bridge.

## What comes next

- **2.35.0** checks the source tracks once for a whole tree instead of before
  every crate, so a tree export stops being slow.

## Known limitations

- **Opciones de exportación** is a screen within the app, so it is opened from a
  review or a saved playlist card; there is no separate menu entry for it.
- A saved card's options screen works from the playlist **as saved**: unsaved
  editor changes are not included, and the screen says so in its source line.
- The app still refuses to commit a crate while Serato DJ Pro or Serato DJ Lite
  is running, because Serato rewrites its crates when it quits.
- The 2.34.0 candidate is source-only: no installer, updater or binary
  redistribution is claimed by this version.
