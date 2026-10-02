# Native Serato checkpoint: temporary fixtures only

This source preview is not a release or permission to write a live Serato library. All native export tests must select a disposable `_Serato_` containing `Subcrates`, beside copied/synthetic music on the same volume. Never select the real Serato folder. Keep a sentinel `database V2` file and hash the copied/original audio before and after.

## Baseline gates

- Install only locked official-registry dependencies; use the isolated Qt-free interpreter and an explicit fresh absolute `XFIN_DATA_DIR`
- Run `XFIN_PYTHON=/absolute/headless/python npm test` in `desktop-electron`; the four integration cases must run, not skip
- Check sandbox/context isolation/no Node in the renderer, no loaded Qt Python modules, and all four Chromium storage paths beneath `XFIN_DATA_DIR`
- Preserve the previously validated v3 source/data separately; do not overwrite the installed Qt app or previous profiles

## Export matrix

1. Scan copies; generate a feasible real Prep selection, review it, then open **Exportar a Serato**
2. Cancel the folder picker. Verify no crate/backup/database/audio change
3. Choose the disposable `_Serato_` (not `Subcrates` itself). Preview the exact track order, name, readiness, warnings and destination. Verify preview creates no output
4. Trigger export and cancel the native final dialog. Verify no output. Trigger again and confirm the fixture write
5. Check receipt, exact binary crate references/readback and source-volume-relative paths; use receipt-only Reveal and confirm the intended file is shown
6. Repeat the same confirmed preview programmatically. It must return the same receipt without another file or backup
7. Preview the same name again and explicitly confirm replacement. Verify the old bytes survive in the exclusive backup and the new bytes validate
8. Save/open a set and export its exact order. Dirty editor changes must block exporting the old saved version until explicitly saved/discarded
9. Rename/edit a saved source, change/remove a track, or alter the target after preview. Confirmation must reject the stale preview without publishing it
10. Exercise blocked/missing-source readiness. `needs_review` remains eligible for explicit confirmation; hard blockers do not
11. Check traversal, extra `confirmed`/`path` fields, invalid IDs and oversized names are rejected by main IPC. Do not send real private paths in negative fixtures
12. Navigate during pending confirmation/publication; successful receipt stays available. Publication is noncancellable; shutdown waits for its completion. Cancelled dirty-close leaves the core usable
13. Verify Spanish status text never includes Electron `xfin:action` wrappers, machine codes or private paths. Technical details belong only in local diagnostics
14. Quit cleanly. Verify child process exit, unchanged original/copy/sentinel hashes and no remaining owned app/core processes

## Filesystem limitations to record

Linux exclusive rename is exercised in cloud tests. macOS uses `renameatx_np(RENAME_EXCL)`; exercise the native branch on the disposable internal-volume fixture. Testing an external filesystem requires a separately authorized disposable destination on that volume. Do not use a live removable Serato root just to prove compatibility.

Creation is no-clobber. Replacement briefly captures/removes the old public filename before no-replace publication, with backup retained. Concurrent arrivals are preserved; failure may leave a named recovery copy for inspection. Unsupported safe primitives fail closed. The new path caps exports at 500 track references and crate IO at 16 MiB; it never truncates an existing saved set.

Controlled dialog responses, muted playback and programmatic screenshots are not human acceptance or audible-output tests. Valid fixture bytes do not prove a live Serato application's import behavior. Report those limits distinctly.
