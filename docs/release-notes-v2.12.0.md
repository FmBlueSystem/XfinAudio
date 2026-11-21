# XfinAudio 2.12.0 Release Notes

Date: 2026-11-15

## Summary

2.12.0 is an **unreleased beta/source candidate** built on 2.11.0. It makes list
preparation easier to understand: Spanish everywhere on the prep and review
screens, a warning before generating about tracks that cannot enter the list,
the quality of every transition in the review table, a fix next to each notice,
and search pickers for the closing, required and excluded tracks.

## Spanish on the prep and review screens

The strategy list and its hint show Spanish names and descriptions. The notices
of a generated list, the descriptions of the alternatives and the transition
explanations are shown in Spanish, keeping their numbers and names, and say what
to do when there is something to do. A notice the app does not recognise is
shown as the engine wrote it.

## Tracks left out, before generating

Tracks without BPM, key or energy cannot enter a generated list. The prep screen
now says so before generating: «12 de 340 pistas no entran en la lista porque
les falta BPM, key.», with **Completar metadatos** to fix them. With fewer than
two complete tracks the app says what is needed and the generate button stays
disabled.

## Transition quality in the review table

The review table has a **Mezcla** column: on each row, how well that track mixes
into the next one, as **Buena**, **Regular** or **Débil** with its percentage
(«Débil · 42 %»), in green, amber and red. Buena is 65 % or more; Débil is below
50 %. It no longer needs **Cargar evidencia local**.

## Each notice with its fix

**Qué revisar** lists every readiness check that is not ready, with its detail
and what to do: complete the metadata, replace or move a track of a weak
transition, replace a repeated track, or generate again with other settings.
The hint of the Live guide button names the checks that are pending instead of
a generic message. When the guide can be opened has not changed.

## Search pickers

**Pista de cierre**, **Pistas obligatorias** and **Pistas excluidas** are chosen
with a search box like the opening track: type to filter by title, artist, genre
or BPM, pick with the keyboard or a click, and remove a chosen track with
**Quitar**. The saved controls and the remembered form work as before.

## Compatibility

The review answer of the local service gains one additive field with the score
of each transition. No stored data changes.

## Known limitations

- Translation is done by recognising the engine's messages; the engine's
  optimizer warnings («Arc subset proven infeasible…») are still in English.
- After **Cargar evidencia local**, the checks that are not ready appear both in
  **Qué revisar** and in the evidence block.
- Only one operation runs at a time; the controls are still disabled during a
  scan or a generation.
- The new controls were verified with automated tests, not yet in a manual
  click-through.
