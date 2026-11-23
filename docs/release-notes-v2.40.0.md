# XfinAudio 2.40.0 Release Notes

Date: 2026-11-22

## Summary

2.40.0 is an **unreleased beta/source candidate** built on 2.39.0. It closes the
two findings of the 2026-11-22 live phase test: **«Pistas por tramo» now looks
disabled** outside **«Cada N pistas»**, and a **short «Pico» run keeps its name**
when it merges into its neighbour. It also changes one rule on purpose: a list
whose whole energy range spans **at most two steps** (for example 6-8) is now
**flat**, exports the parent alone, and says so with the **«casi pareja»** notice.
That last change was the DJ's own decision after the live test, and it replaces
the **«under a fifth of the scale»** floor that 2.37.0 introduced.

## «Pistas por tramo» looks disabled outside «Cada N pistas»

The input was already disabled for **«Por fases de energía»** and **«Sin dividir»**,
but the author's input colours painted it as an editable field in the dark theme,
so a disabled control looked like a live one. The fix is an id-scoped style on
`#serato-export-split-size:disabled`: muted text, recessed background, a dimmed
border and a `not-allowed` cursor.

What the DJ sees now:

- In **«Por fases de energía»** and **«Sin dividir»** the field is **visibly
  disabled**, not editable, and still announced as disabled to assistive
  technology.
- In **«Cada N pistas»** it is enabled again, and **the number typed earlier is
  kept**, so switching modes back and forth does not reset the size.
- The help text is unchanged and still says the choice belongs to that export
  only.
- Both entry points — the review screen and a saved playlist's **«Opciones de
  exportación»** — show the same state, because they render one shared view.

## A short «Pico» keeps its name after merging

A phase shorter than two tracks joins the neighbour with the nearest mean energy,
and the merge used to keep the **absorbing neighbour's** name. That is how the
peak disappeared: a rise-and-fall set came out as Apertura + Cierre with no Pico
at all.

After merging, the run that holds the **top of the smoothed curve** (its first
maximum) is now called **«Pico»**. Every other run keeps its name, the phase names
stay in the order **Apertura, Subida, Pico, Cierre**, and the numbering and track
ranges stay contiguous and cover every track exactly once.

The two merge directions that used to lose the peak now keep it:

| Merge direction | Plan |
|---|---|
| backwards into «Apertura» | `Apertura (1-3)`, `Pico (4-7)`, `Cierre (8-12)` |
| forwards into «Subida» | `Apertura (1-3)`, `Subida (4-7)`, `Pico (8-10)` |

This applies to lists that **do** split. A list that is flat keeps the parent
alone, as described next.

## A list within two energy steps is flat

A list whose whole energy range spans **at most two steps** of the 1-10 scale is
treated as **almost even**: it is not split, and the export keeps the **parent
alone** with the existing `flat` reason and its Spanish sentence.

- **Two steps are flat**: 2/9 = 0.222, so a list that only moves between, say, 6
  and 8 exports as one crate.
- **Three steps still split**: 3/9 = 0.333, and a list that really rises gets its
  phases, **exactly the same plan as in 2.39.0** when it already contains a
  «Pico».

Why this threshold: on the live set **«Sesión equilibrada»** (20 tracks, energy 7
almost everywhere with 8s at tracks 8 and 11) the new peak naming produced
`1 Pico (1-8)` + `2 Cierre (9-20)` — a «Pico» starting at track 1 of a list that
never really leaves level 7. That plan was withheld and handed to the DJ, who
chose **«tratarla como plana»**: a list that stays within two steps is not a
journey.

Nothing else in the planner moves: the other skip reasons, the smoothing and the
other thresholds are unchanged, and no audio or live Serato database V2 file is
touched.

## Side effect: one- and two-step lists say «casi pareja»

Because the floor now covers two steps, a list that used to be a **single phase**
or was **just under the old floor** can land on the `flat` reason instead. When
that happens the preview shows the flat sentence —

> «La energía de la lista es casi pareja; no hay fases claras y se exportará sin dividir.»

— where it used to show **«una sola fase»**. Both sentences end in the same
outcome, the parent alone; only the wording changes, and the core still sends the
reason while the screen owns the sentence.

## Live examples after this change

- **«Sesión equilibrada»** (20 tracks): energy 7 on tracks 1-7, 8 on track 8, 7
  on 9-10, 8 on 11, 7 on 12-16, 6 on 17, 7 on 18-20; smoothed curve
  `0.5×6, 0.625, 0.75, 0.625, 0.625, 0.75, 0.625, 0.5×3, 0.375, 0.25, 0.375, 0.5, 0.5`.
  Planned in 2.39.0 as `1 Apertura (1-8)` + `2 Cierre (9-20)` — no Pico. After
  2.40.0 it is **flat**: the parent alone, with the «casi pareja» notice.
- **«22 nov»**: energy 7 everywhere except 8 on tracks 6 and 18, a range of
  0.111. It was already flat in 2.39.0 and it is **still flat**, for the same
  reason, with the same notice.

## How it was verified

- Planner: **RED 3 failed -> GREEN 27 passed**, then **208** phase and export
  tests, **full suite 3777 passed**, `ruff` and `pyright` clean.
- Differential over **20,000 random lists** against the previous code: the
  **11,340** that already had a «Pico» get an identical plan, and every other
  difference is either becoming flat or one rename to «Pico».
- Renderer: **RED 14/15 -> GREEN 15/15**, then **64** renderer tests passing and
  `tsc` clean, covering phases / none / every, the kept value, the assistive-tech
  state and both entry points.
- Release metadata: `tests/test_electron_candidate_metadata.py` and the public
  docs tests pass; `pyproject.toml`, `uv.lock`, `desktop-electron/package.json`,
  `desktop-electron/package-lock.json` and this file agree on **2.40.0**.

## Known limitations

- The flat floor deliberately hides the phases of a real two-step journey: a list
  that moves between 6 and 8 is exported as one crate even if a DJ would hear a
  rise in it. That was the explicit choice made after the live test, and it
  replaces the 0.2 floor.
- One- and two-step lists that used to say «una sola fase» now say «casi pareja».
  The wording changed on purpose; the outcome did not.
- The «Pico» naming applies only to lists that split; a flat list has no phases
  to name.
- The 2.40.0 candidate is source-only: no installer, updater or binary
  redistribution is claimed by this version.
