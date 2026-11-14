# XfinAudio 2.7.0 Release Notes

Date: 2026-11-13

## Summary

2.7.0 is an **unreleased beta/source candidate** built on 2.6.0. It removes two
points where the user had to know something the app could find: the Serato
destination folder and the opening track of a set.

## Serato export

The export screen no longer starts by asking for a folder. When it opens with a
selection to export it looks for `_Serato_` on its own: first under each scanned
library folder, then at the root of the music drive (a library in
`/Volumes/dd/_Lossless/por_genero` uses `/Volumes/dd/_Serato_`), and finally in
`~/Music` when that folder is on the same volume. A destination found this way is
shown as detected automatically and the screen goes straight to the preview
step; **Cambiar carpeta _Serato_** keeps the manual picker as a secondary action.
When nothing is found, the screen says so in Spanish, explains that opening
Serato once with the drive connected creates the folder, and offers the manual
choice instead of opening a dialog on its own. A folder chosen by hand may now be
the drive root or `~/Music`: the `_Serato_` folder it directly contains is used,
and anything else keeps the existing `invalid_destination` refusal. Detection and
registration keep the same-volume rule, canonical folder and backup checks as
before, and nothing is written until the final confirmation.

Exporting itself is now two actions instead of a walk through separate screens.
From a generated set on the review screen or from a saved playlist card, one
**Exportar a Serato** click runs detection and the preview in the background and
opens the system confirmation with the crate name, the destination path, the
track count, whether the crate is new or replaced with a backup, and the
warnings; confirming is the second action and still the only write consent. The
result is reported where you are, without changing screen: **Crate «name»
exportado a Serato** with a **Mostrar en Finder** action, the blockers in
Spanish when the preview refuses to export, or **Elegir carpeta** when no
destination was found, which continues to the same confirmation after a valid
choice. The export screen remains one click away as **Opciones de exportación**
for renaming the crate or changing the folder, and metadata worklist exports keep
their current page flow.

A local service restart no longer turns into a folder prompt: the app forgets the
Serato ids the stopped core held, finds `_Serato_` again on the next export, and
if a preview still carries an id the new service does not know it re-detects once
and retries that preview once — you are never asked to choose a folder detection
can find, and the confirmation, backup and same-volume checks are unchanged.

Crate names for generated sets are now short and automatic — the style plus the
export date, **Harmonic Journey 14-nov**, then **(2)** and **(3)** when that crate
already exists in `Subcrates`, so an automatic name never replaces a different
earlier export — while a name you type on the export screen and a saved
playlist's name are used exactly as they are.

## Opening track search

The Prepare screen no longer makes you scroll a full library list to pick the
opening track. **Pista de apertura** is now a search box: type a title, artist,
key, genre or BPM, with or without accents, and up to ten matching tracks appear
with their BPM and key, chosen with the arrow keys and Enter or a click. The
chosen track stays visible with a **Quitar** action; leaving it empty still
generates the set without an opening track. The closing, required and excluded
track pickers are unchanged in this release.

The library search box shares the same matcher, so it now also finds tracks by
BPM and ignores accents; it never loses a match it found before.

## No repeated songs in generated sets

A generated set no longer holds the same song twice under different metadata.
The candidate pool already collapsed duplicate versions before choosing the
running order; it now also recognises the differences DJ pools invent for one
recording, so **YMCA**, **Y.M.C.A.**, **YMCA (Hot Tracks)** and **Y.M.C.A. (DJ
Edit)** count as one song, as do **The Village People** and **Village People**.
Punctuation and accents are ignored (**Y.M.C.A.** = **YMCA**, **I've** =
**Ive**, **Brújula** = **Brujula**), one leading article is ignored on the
artist, and a row with no artist whose title reads **Artist - Title** takes its
artist from the title — which is how the two **The Killers - All These Things
I've Done** rows with a blank artist are recognised. Tracks you pin (opening,
closing or required) are still never removed, and the duplicate warning in the
readiness check uses the same improved comparison. Different songs stay
different: the same title by another artist, a title that only differs in its
words, and a blank-artist row with no **Artist - Title** form are not merged.

## Core restart

When the local service stops, the app still says so, but a supervised restart now
brings it back on its own: once the replacement service is up and its libraries
are ready, the screen returns to its normal state and the operations you were
using work again, with no need to quit XfinAudio. Only when the restart attempts
are exhausted does the app keep the existing message asking you to restart it.

## Compatibility

- macOS only, unchanged. No Serato database V2 writes.
- The Electron shell and the headless core agree on version 2.7.0.

## Known limitations

- These screens have been checked by the automated suites, not yet clicked
  through in a running app.
- With a real core, the Electron integration test in
  `desktop-electron/tests/serato.integration.test.mjs` fails locally on this
  candidate and on 2.6.0 alike; it passes in CI.
