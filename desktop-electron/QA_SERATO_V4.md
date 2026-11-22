# Native Serato checkpoint: temporary fixtures only

This source preview is not a release or permission to write a live Serato library. All native export tests must select a disposable `_Serato_` containing `Subcrates`, beside copied/synthetic music on the same volume. Never select the real Serato folder. Keep a sentinel `database V2` file and hash the copied/original audio before and after.

## Baseline gates

- Install only locked official-registry dependencies; use the isolated Qt-free interpreter and an explicit fresh absolute `XFIN_DATA_DIR`
- Run `XFIN_PYTHON=/absolute/headless/python npm test` in `desktop-electron`; the four integration cases must run, not skip
- Check sandbox/context isolation/no Node in the renderer, no loaded Qt Python modules, and all four Chromium storage paths beneath `XFIN_DATA_DIR`
- Preserve the previously validated v3 source/data separately; do not overwrite the installed Qt app or previous profiles

## Export matrix

1. Scan copies; generate a feasible real Prep selection, review it, then click **Exportar a Serato** on the review screen (or on a saved playlist card). With a disposable `_Serato_` holding `Subcrates` inside the copied library folder (or at its volume root), detection finds it automatically and the click goes straight to the system confirmation. Preview the exact track order, name, readiness, warnings and destination, and verify the preview creates no output
2. With no disposable `_Serato_` on the volume, the screen must say so in Spanish and offer **Elegir carpeta**, not open a dialog on its own. Use **Cambiar carpeta _Serato_** (or **Elegir carpeta**) from **Opciones de exportación** to choose the disposable `_Serato_`, never `Subcrates` itself. A valid choice continues to the same confirmation; cancelling the chooser leaves no output and keeps the current screen usable
3. Cancel the system confirmation. Verify no crate/backup/database/audio change
4. Trigger the export again and confirm the fixture write. The confirmation shows the crate name, the destination path, the track count, whether the crate is new or replaced with a backup, and the warnings
5. Check the automatic crate name for a generated set: the style plus the export date, then **(2)** and **(3)** when an earlier export already holds that name, and no replacement of that earlier crate. For a nested name, verify the parent crates are created in the same confirmed export and named in the confirmation and in the preview; an existing parent is never rewritten, replaced or backed up
6. Confirm an export with Serato DJ Pro or Serato DJ Lite running (or start Serato before confirming): it must be refused in Spanish and nothing written, with no crate, backup or database change. Closing Serato and confirming the same preview exports without a new preview
7. Check receipt, exact binary crate references/readback and source-volume-relative paths; use receipt-only Reveal and confirm the intended file is shown
8. Repeat the same confirmed preview programmatically. It must return the same receipt without another file or backup
9. Preview the same name again and explicitly confirm replacement. Verify the old bytes survive in the exclusive backup and the new bytes validate
10. Save/open a set and export its exact order. Dirty editor changes must block exporting the old saved version until explicitly saved/discarded
11. Rename/edit a saved source, change/remove a track, or alter the target after preview. Confirmation must reject the stale preview without publishing it
12. Exercise blocked/missing-source readiness. `needs_review` remains eligible for explicit confirmation; hard blockers do not
13. Check traversal, extra `confirmed`/`path` fields, invalid IDs and oversized names are rejected by main IPC. Do not send real private paths in negative fixtures
14. Navigate during pending confirmation/publication; successful receipt stays available. Publication is noncancellable; shutdown waits for its completion. Cancelled dirty-close leaves the core usable
15. Verify Spanish status text never includes Electron `xfin:action` wrappers, machine codes or private paths. Technical details belong only in local diagnostics
16. Quit cleanly. Verify child process exit, unchanged original/copy/sentinel hashes and no remaining owned app/core processes

## Filesystem limitations to record

Linux exclusive rename is exercised in cloud tests. macOS uses `renameatx_np(RENAME_EXCL)`; exercise the native branch on the disposable internal-volume fixture. Testing an external filesystem requires a separately authorized disposable destination on that volume. Do not use a live removable Serato root just to prove compatibility.

Creation is no-clobber. Replacement briefly captures/removes the old public filename before no-replace publication, with backup retained. Concurrent arrivals are preserved; failure may leave a named recovery copy for inspection. Unsupported safe primitives fail closed. The new path caps exports at 500 track references and crate IO at 16 MiB; it never truncates an existing saved set.

Controlled dialog responses, muted playback and programmatic screenshots are not human acceptance or audible-output tests. Valid fixture bytes do not prove a live Serato application's import behavior. Report those limits distinctly.
