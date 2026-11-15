# XfinAudio 2.8.0 Release Notes

Date: 2026-11-14

## Summary

2.8.0 is an **unreleased beta/source candidate** built on 2.7.0. It makes two
points of the Prepare flow say what they know: the preferred genre is chosen from
a list that puts the genres compatible with your opening track first, and every
operation you start shows whether it is still working, where it is, or how it
ended.

## Choose the genre from a list

**Género preferido** is no longer a text box hidden under *Afinar selección*. It
sits on the Prepare screen next to **Pista de apertura**, because the two answer
the same question: where the set starts. Click it, or move to it with the
keyboard, and the list of your library genres opens without typing. Type to
filter, move with ↑ ↓, choose with Enter or a click, and **Quitar** clears the
choice. One genre only.

Every option shows the genre as your library stores it and how many tracks it
holds — **Deep House (124)** — and genres that differ only in case or accents are
counted and matched as one, the same way the engine compares them. Without an
opening track the list is ordered by track count, most first.

## Compatible genres first

When an opening track is chosen, the list opens as two groups. The first,
**Compatibles con «<título de la semilla>»**, starts with the seed's own genre and
then lists the genres of the library tracks that mix best with it — close BPM
(including half and double time), a compatible Camelot key and a similar energy —
most useful genre first. The second, **Resto de la biblioteca**, holds every other
genre in alphabetical order. The ranking comes from the core, which already
scores those transitions, so the list and the engine never disagree. Changing the
opening track updates the list, and a genre you had already chosen stays chosen.

The choice still travels to the engine as `genreFocus` with the same validation
and the same saved-settings restore as before. A restored genre that is no longer
in the library is shown as unavailable instead of being silently replaced, like
the opening track.

## Clear progress states

The status area now tells you three things instead of one. **En curso**: an
animated indicator, the name of the operation, the stage it is in and which step
of the job it is — «Paso 2 de 2 · Completando perfiles · 340 de 1 200» — with a
progress bar when the core reports counts and a plain activity line when it does
not, while the button that started it shows it is working. **Listo**: a green
check with the result — «✓ Biblioteca actualizada · 10 391 pistas» — that settles
after a few seconds into a discreet line with the last result. **Error** or
**cancelado**: red, with the reason, and it stays until you start the next
operation. The region is marked busy while it runs and announces the end to a
screen reader.

## Named stages

Chained work now reads as one job with numbered steps, so scanning and then
completing profiles automatically is «Paso 1 de 2» followed by «Paso 2 de 2»
instead of two unrelated messages. Generating a set shows the core's own stages
in Spanish — **Preparando alternativa segura**, **Preparando alternativa
equilibrada**, **Preparando alternativa aventurera**, then **Finalizando la
preparación** — instead of the generic «Preparando selección…», and the bar
follows the 0–3 of 3 checkpoints the core reports. Operations that
emit no progress today — opening an alternative, saving a playlist, the Serato
export, the metadata review and the legacy import — show the same indeterminate
running state and a done state, so nothing finishes without saying so.

## Compatibility

- macOS only, unchanged. No Serato database V2 writes.
- The Electron shell and the headless core agree on version 2.8.0.

## Known limitations

- These screens have been checked by the automated suites, not yet clicked
  through in a running app.
- Idle background reads still go through the same status path, so a read that
  arrives after a failure can replace a red error line within a second.
- With a real core, the Electron integration test in
  `desktop-electron/tests/serato.integration.test.mjs` fails locally on this
  candidate and on 2.7.0 alike; it passes in CI.
