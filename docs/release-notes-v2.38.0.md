# XfinAudio 2.38.0 Release Notes

Date: 2026-11-22

## Summary

2.38.0 is an **unreleased beta/source candidate** built on 2.37.0. It is the
third and last part of the profiles-and-phases work, and it opens the capability
2.37.0 could only plan: **Dividir en tramos** on **Opciones de exportación** now
offers a third choice, **«Por fases de energía»**, which splits the exported set
into **Apertura**, **Subida**, **Pico** and **Cierre** crates from the tracks'
own energy instead of from a fixed size.

## The third choice

**Dividir en tramos** offers three choices, and the first is still the default:

- **No dividir** — the single crate described in the 2.35.0 notes.
- **Cada N pistas** — one child crate per N tracks.
- **Por fases de energía** — one child crate per energy phase of the set.

**«Pistas por tramo» is disabled in that mode**, because a phase split derives its
own boundaries. The number the DJ typed for **Cada N pistas** is kept, so going
back to it restores the size instead of resetting it. The hint under the control
says what the mode does, that a set of at least 8 tracks is needed, that a set
which cannot be split is exported without splitting, and that the choice belongs
to that export only.

## What the preview and the confirmation show

A phase tree is one tree with one confirmation, exactly like a fixed-size tree.
The preview lists the parent crate first with every track in the reviewed order,
then one indented child per phase with its name and its track count and whether
it is created or replaced:

```text
XfinAudio › 22 nov › 1 Apertura (1-4)
XfinAudio › 22 nov › 2 Subida (5-12)
XfinAudio › 22 nov › 3 Pico (13-19)
XfinAudio › 22 nov › 4 Cierre (20-26)
```

The native confirmation lists the same crates, with the same names and counts,
and previewing still writes nothing.

## When a set cannot be split, the preview says why

No phases are invented. When the set has no phases the parent is exported **alone**
— one crate, the same as **No dividir** — and the preview adds **one Spanish
sentence**, in the DJ's own vocabulary rather than a code:

| The set cannot be split because | What the preview says |
|---|---|
| the list is too short | «La lista es muy corta para dividirla por fases (mínimo 8 pistas); se exportará sin dividir.» |
| energy data is missing | «Faltan datos de energía en la lista; se exportará sin dividir.» |
| the energy is almost even | «La energía de la lista es casi pareja; no hay fases claras y se exportará sin dividir.» |
| the energy forms one phase | «La energía de la lista forma una sola fase; se exportará sin dividir.» |

The core sends the **reason**; the screen owns the sentence. A reason added by a
newer core is ignored by an older screen instead of printing an unknown text, and
the preview then simply holds no phase sentence.

## The split mode is a closed vocabulary

- `serato.preview` accepts **`splitMode`** with exactly three values: `none`,
  `every` and `phases`. An **absent** mode is today's contract: the tramo size
  alone decides, so every existing caller behaves as before.
- A phase split **ignores** any tramo size sent with it, and `none` keeps the
  single crate even when a size is present. An explicit `every` previews the same
  tree as a size alone.
- The IPC accepts only those three words: anything else is refused before any
  work starts.
- A **metadata worklist** is not a set: both a tramo size and an energy split are
  refused for it, as before.
- **Quick export never splits.** A one-click export from the review screen or from
  a saved playlist card still writes exactly one crate.

## Naming and re-exporting are unchanged

The tree is planned by the same core function 2.37.0 introduced, so the children
carry `<n> <Fase> (<first>-<last>)` under the parent's own name: a saved playlist
name or a typed name becomes **XfinAudio › `<name>`** with its children under it,
an automatic name takes the first number free for the parent and every child at
once, and re-exporting an automatic name that already exists moves the **whole new
tree** to `(2)`. An older tree's children are never deleted, moved or renamed.

## Nothing else changes

- **No split and every-N are untouched**: the same previews, the same names, the
  same bytes and the same receipt as in 2.37.0.
- The tree still carries the caps of **500 track references** and **16 MiB** per
  crate, the **stale-preview** refusal, the **Serato-running** refusal, the
  all-or-nothing rollback, and it still writes **no live Serato database V2**
  file and mutates **no audio** outside loudness tag writing.
- **Opciones de exportación** is still opened from a review or a saved playlist
  card; there is no separate menu entry for it.

## Known limitations

- **The live Serato check of a phase tree is pending.** Everything above is
  proven against a disposable fixture folder; opening a phase tree in Serato DJ
  Pro is to be recorded after release, together with how Serato shows a parent
  crate that contains its children's tracks, and whether a track appears both in
  the parent and in its own phase crate. If it does, that is the behaviour to
  document, not to change here.
- A set that cannot be split is offered no way to force phases; the export is the
  parent alone and the preview says why.
- The phases follow the reviewed order, so reordering the same tracks can change
  the phases.
- The 2.38.0 candidate is source-only: no installer, updater or binary
  redistribution is claimed by this version.
