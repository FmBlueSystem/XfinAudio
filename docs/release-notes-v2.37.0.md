# XfinAudio 2.37.0 Release Notes

Date: 2026-11-22

## Summary

2.37.0 is an **unreleased beta/source candidate** built on 2.36.0. It is the
second part of the profiles-and-phases work, and it is a **planning capability
only**: the exporter can now plan a Serato crate tree by the **set's own energy
phases** — `Apertura`, `Subida`, `Pico` and `Cierre` — with one child crate per
phase instead of one child per N tracks.

**No screen offers it yet.** The core can plan it and its tests prove it, but the
export options screen, the protocol field and the preview still know only
**Dividir en tramos**; the **«Por fases de energía»** option arrives in **2.38.0**.
Nothing is written until a confirmed export, and nothing new is written by this
version.

## The phases come from the set, not from the strategy

The phases are read from the **tracks' own Mixed In Key energy** (1-10) in the
order the set is reviewed. They are never read from the strategy: a saved
playlist carries no strategy of its own, so reading one would invent a journey
that the music does not have.

A track without an energy takes the **nearest known energy before it**, or the
first known one when the gap comes first, so a missing value can never swing the
curve.

## The curve is smoothed before it is read

The known energies are normalised to the set's own lowest and highest value, then
smoothed with an edge-clamped three-point moving average — the track itself
weighs half, each neighbour a quarter — and rounded to three decimals. One odd
track can therefore not open a phase of its own.

The whole computation is a **pure function of the ordered energies**: the same
list always splits the same way, with the same phase boundaries, in every run.

## Apertura → Subida → Pico → Cierre

- **Apertura** is everything before the curve first rises.
- **Subida** is the climb up to the highest point; a second, lower peak on the way
  belongs to the climb, not to a phase of its own.
- **Pico** is the plateau at the top: every track within a tenth of the maximum,
  around the first maximum.
- **Cierre** is everything after that plateau.

A phase with no tracks is not a phase and is dropped (an ascending set, for
example, ends on its peak and has no `Cierre`). A phase shorter than **two
tracks** merges into the neighbour nearest in mean energy, so **every phase holds
at least two tracks** and the phases cover the set end to end without a gap.

## Children are named after their phase

Each child is named `<n> <Fase> (<first>-<last>)`, with the 1-based positions of
its first and last track in the reviewed order. A tree the DJ names **22 nov**
holds:

```text
XfinAudio › 22 nov › 1 Apertura (1-4)
XfinAudio › 22 nov › 2 Subida (5-9)
XfinAudio › 22 nov › 3 Pico (10-12)
XfinAudio › 22 nov › 4 Cierre (13-20)
```

An automatic tree keeps its own automatic name in place of `22 nov`, and its
children carry the same short date.

The parent naming is exactly the one 2.35.0 shipped: a saved playlist name or a
name typed on the options screen becomes the crate **XfinAudio › `<name>`** and
its children follow it, while an automatic name takes the **first number free for
the parent and every child at once**, so a tree that already exists moves to
`(2)` as a whole. Leaf names pass the same sanitising as every other crate name,
and a name that already carries the `XfinAudio` prefix is never doubled.

## When the set has no phases

The parent is exported alone, exactly as a single crate, and the plan carries the
reason so a screen can explain it:

| Reason | When |
|---|---|
| `too_few_tracks` | the list has fewer than **8** tracks |
| `too_few_energies` | fewer than **2** tracks have an energy |
| `flat` | the range is under **a fifth** of the 1-10 span (less than two steps) |
| `single_phase` | the curve is one band, so no phase boundary survives |

An alternating set that clears the flat floor with a two-step range, for example,
still names no phase: it is one band, not a journey.

## Nothing else changes

- **The two existing tree shapes are unchanged**: a `segment_size` plan and a
  no-split plan produce the same parent, the same children, the same bytes and
  the same names as in 2.36.0, checked against the generated single crate and
  across both spellings of the segment mode (`segments` and an absent mode). The
  tracks' energies change nothing there, and neither shape carries a phase
  reason.
- The split mode is validated explicitly: only `segments` and `phases` are
  accepted, an absent mode means `segments`, and anything else is refused with
  *split mode must be segments or phases*. A leftover segment size in phases mode
  changes nothing.
- The segment size rules (**2 to 50**) are untouched, as are the caps
  (**500 track references** and **16 MiB** per crate), the **Serato-running**
  refusal, the **stale-preview** refusal, the all-or-nothing rollback and the
  rule that no live Serato database V2 file is written.

## Known limitations

- **There is no screen for it yet**: the export options screen still offers
  **Dividir en tramos** only, and neither the bridge nor the preview carries a
  split mode. The **«Por fases de energía»** option, its Spanish reasons and its
  preview text arrive in **2.38.0**.
- This version **plans, it does not write**: the export flow, its preview, its
  confirmation and its rollback are unchanged.
- The phases follow the **reviewed order**. Two runs of the same ordered list are
  always identical, but reordering the same tracks is allowed to change the
  phases, because the set is the journey.
- The reason for a set without phases is on the plan; a screen only shows it from
  2.38.0.
- The 2.37.0 candidate is source-only: no installer, updater or binary
  redistribution is claimed by this version.
