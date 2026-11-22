# XfinAudio 2.29.1 Release Notes

Date: 2026-11-22

## Summary

2.29.1 is an **unreleased beta/source candidate** built on 2.29.0. It is a
hotfix: **«Exportar a Serato» on the review screen now exports an opened saved
playlist**, a **refused export says so in Spanish** next to the button instead of
staying silent, and the **real-core Serato integration test only touches its own
temporary fixture** instead of the machine's Serato folder.

## An opened saved playlist exports from the review screen

A saved playlist opened on the review screen did nothing when the DJ pressed
**«Exportar a Serato»**: the click stopped before reaching the local core, so no
dialog opened and no log line followed the core start. The screen sent the
playlist identity as a JSON number while the desktop shell accepts only the
decimal string it validates for every export source, and the refusal was never
shown. The review payload now carries the playlist id as that same decimal
string the saved-playlist card already used, so the export reaches the same
destination detection, preview, native confirmation and receipt as the card's
own **«Exportar a Serato»** button. Saving a list's edits in place keeps the
identity string too, so the button keeps working after a later edit.

The shell's validation itself is unchanged: only a decimal string is accepted,
and a number is still refused rather than quietly converted.

## A refused export explains itself next to the button

When the shell refuses an export request, the quick-export notice now shows a
Spanish message beside the export button — the reason when the refusal carries
one, and a short generic sentence otherwise — so a click can no longer look
ignored. The Serato-open refusal keeps its own wording, and a failed
**«Mostrar en Finder»** is not reported as an export that did not start.

## The Serato integration test never writes to the machine's Serato folder

The real-core test that previews, confirms and commits a crate through the local
core used to call automatic destination detection like the app does. On a
machine that has `~/Music/_Serato_`, that detection won over the test's own
fixture: the test replaced a crate of that folder and left its backups behind.
The test now runs the core with its home directory and library root inside its
temporary fixture, records what discovery answers and never lets any folder
outside the fixture reach registration, and asserts that the crate it writes
lands in the fixture's `Subcrates` folder. The machine's own `_Serato_` folder
is no longer a possible destination of the test.

## What does not change

- The export boundaries stay as they were: no path, destination or confirmation
  flag crosses the bridge, and no live Serato database V2 file is written.
- Metadata scanning stays read-only, and no audio file is mutated outside
  loudness tag writing.
- Destination detection, the manual folder choice, the preview, the native
  confirmation and the per-export receipt behave as in 2.29.0.
- The Playlists card's **«Exportar a Serato»** keeps sending its own validated
  source and exporting the stored playlist.

## Known limitations

- The core still refuses to commit a crate while Serato DJ is running, because
  Serato rewrites its crates when it quits. The integration test inherits that
  guard: it commits in CI, where Serato is not running, and on a machine whose
  Serato has been closed.
- The 2.29.1 candidate is source-only: no installer, updater or binary
  redistribution is claimed by this hotfix.
