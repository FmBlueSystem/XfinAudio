# V7 native fixture verification: loudness and automatic tag writing

## Scope and fixtures

Materialize V7 separately and keep V6 source/data immutable. Use an explicitly isolated XFIN_DATA_DIR and the Qt-free Python interpreter. Use fresh disposable copies or generated synthetic audio: this slice intentionally changes their loudness tags/comments after native confirmation. Original music, the V6 copies and live Serato remain read-only. Do not run against a whole real library.

FFmpeg must be available from an existing trusted installation/bundle for source-mode execution. Record its exact version/path/provenance. If absent, verify the truthful unavailable state and report the missing prerequisite; do not change OS/security settings or fetch an unknown binary. Bundled-Python/FFmpeg packaging remains later work.

IMPORTANT: loudness-backups/*.bak contains complete original audio bytes. Keep backups local. Never upload the backup directory, .bak files, copied music or originals as an evidence bundle. Evidence may contain reports, hashes, JSON recovery manifests and screenshots only.

## Automated baseline

Run `XFIN_PYTHON=<Qt-free Python> npm test`. No opt-in skips. The real FFmpeg test loops the repository-owned synthetic tone into a disposable 65-second FLAC, measures/writes it, validates an exact original-byte backup and compares decoded PCM SHA256 before/after. It also checks cache replay without another backup. Record all counts and exit status.

## Native application matrix

1. Scan fresh synthetic/copy fixtures. Open Sonoridad: no audio changes on screen load, settings Save or scope preview. Original enabled default true, target −10 LUFS and tolerance 2 LU remain; enabling never silently starts a new-runtime write. Show real engine availability and state/value distinctions.
2. Update target/tolerance within bounds, restart and verify persistence. Invalid/missing/nonfinite values and arbitrary path/command/confirmed payloads fail closed. The configured LoudnessBand must reach candidate planning and Prep generation. Unrelated preferences are preserved.
3. Select a bounded explicit scope, inspect read-only preview and backup estimate. Cancel the native confirmation: all source/copy hashes remain identical and no backup/run starts. Unknown preview IDs, duplicate/unknown track IDs, over500 scope and multi-track force-reanalysis reject. Single-track force works.
4. Confirm one or two fresh disposable files. Verify actual finite LUFS/LRA/dBTP and correct state. Complete profiles write the original format tags/comment policy. FLAC DESCRIPTION preserves foreign text while refreshing its loudness suffix. Short/incomplete/unsupported measurements are not presented as complete.
5. For each changed copy, validate the .bak original bytes against its pre-run SHA256. Its adjacent .bak.json records originalPath, originalBytes, SHA256 and backupFile. Compare decoded audio samples before/after; do not infer audio-content preservation solely from FLAC's stored MD5 field. Read back tags independently.
6. Repeat from a fresh preview without force: cached profiles produce no analysis/write/extra backup. Force one unchanged measured track: tags remain idempotent and no extra backup is created.
7. Replace/change/delete a disposable source after preview, or change settings/rescan: the old scope cannot run. Also change a file before preview without rescanning: stale scanner metadata/duration must be rejected. A historical profile on a changed file is hidden until verified/rescanned.
8. Cancellation during analysis reaches the original process-group cancellation and reaps children. Cancellation/close during a controlled held metadata commit waits for that commit, returns truthful modified/failed/backup counts, and retains its backup. This is a controlled publication-boundary test, not evidence of physical slow/removable I/O.
9. Cancel while native confirmation is pending, then resolve that test dialog affirmatively: no writer starts. Cancel a dirty-close dialog: core/drafts remain usable. Dirty editor or ordinary preference drafts block loudness preview/run until Save/Discard. All three draft types jointly protect closing.
10. Own metadata write notifications are suppressed only for their exact paths for up to five seconds. Another file's change must still invalidate stale Prep/Live/Serato context; later changes to the same file must be detected after expiry. Suppression is advisory and is not a permission grant.
11. Simulate a fixture-only cache/status failure after a completed write: retain counts and backups, show a safe warning, and keep returned fallback tracks informational. A warning must not disappear into a raw transport error or revive stale context. Partial-save failure retains original bytes for recovery; do not claim universal filesystem rollback.
12. The recovery button reveals only the fixed isolated backup directory. No path parameter exists; redirects/symlinks are refused. Empty state is honest. No automatic restoration action is introduced.
13. Re-run baseline readonly scan, Prep/review/save/editor, Live, muted FLAC playback and temporary Serato regression using separate non-mutated baseline fixtures. Compare original music/V6 data/Serato sentinel hashes and leave zero owned workers/Python/FFmpeg processes.

## Limits

Controlled dialogs are not human acceptance; muted programmatic playback is not audible acceptance. Native macOS/removable filesystem behavior and long-running sessions require explicit results. Scope is at most 500 selected tracks per run, with one-track force-reanalysis. Native permission/confirmation gates are new-runtime safety controls; this preview does not automatically schedule writes immediately after a scan. AI/provider functionality and standalone distribution remain subsequent migration slices.
