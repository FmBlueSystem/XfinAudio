# Focused verification

Date: 2026-10-01. All fixtures are generated under the workspace. No real legacy HOME paths, credentials, live Serato, providers, original audio, installed application replacement or release operations were used.

## Results

- Qt-free V9 environment: `PYTHONPATH=src .venv/bin/python -m pytest --noconftest -q tests/test_headless_legacy_import.py --basetemp=/workspace/scratch/f7681295be42/legacy-final-headless-tests`: **30 passed**.
- Electron `npm run build`: **passed**.
- Node tests `legacy-import-host.test.mjs`, `legacy-import-renderer.test.mjs`, `renderer.legacy-app.test.mjs`: **12 passed** (5 native host, 4 controller, 3 shared-owner composition).
- Focused `ruff check`, `ruff format --check`, and Pyright with the verification interpreter: **passed**.
- The full repository gate is pending separately. No packaging, installed-app replacement or macOS acceptance claim is made.

## Requirement evidence

Native-only authority and cancellation: host tests prove path is selected only natively, raw path/confirmed field never reach renderer, confirmation owns confirmed:true, forged token fails, and pending confirmation cannot race close.

Read-only bounded preview: exact selected folder only; nofollow descriptor walk protects every ancestor and leaf; source SQLite is deserialized in memory, not opened on disk; WAL/SHM/journal rejection includes empty sidecars. Supported schema is current track schema 6 and exact playlist schema 0. Corrupt/oversized/unknown schemas/triggers/profiles/order/dates and lexical external paths reject. Test source database/settings/audio hashes remain identical.

Fresh-profile contract: existing tracks, playlists, settings or root grants refuse import. Preview/destination changes and late grants invalidate it. Safe volume/cohesion are copied; AI credentials/source/enablement, watcher, loudness and Serato enablement/grants are excluded or disabled.

Persistence/recovery: repository schema and model readers validate in-memory rebuilt caches and playlists; original order and current profile identities survive restart. Single-instance main guard plus per-publish byte comparisons and no-clobber publication prevent silent overwrite. Backups/outgoing/interrupted bytes remain retained. Crash/partial disk failure restores the prior profile; unexpected newer data blocks recovery rather than overwrites it. A committed-journal sync failure truthfully requires restart instead of claiming rollback.

Authorization after import: backend and native host refuse further work until restart; renderer composition stops playback/watch and freezes routes even on uncertain commit/reload. Restart exposes zero library tracks until separately authorized root selection/rescan; cache and playlist references remain quarantined.

## Explicit limits

Fresh-profile-only, current schemas only, no automatic legacy discovery, no merge/overwrite, 256 MiB per database, 256 KiB settings, 100,000 tracks, 5,000 playlists, 250,000 references, 20 preview names and retained preview workspaces. The old app must be closed with no pending SQLite sidecars; an unsupported or WAL-dependent source needs a checkpointed compatible copy/export before use. Backups are not automatically deleted; only disposable publication temporary links are removed.

## Aggregate gate correction: canonical startup contract

The original loudness integration alias-negative case was reproduced RED because the strengthened startup check now refuses a symlinked application-data directory before repositories open. The test was updated to require that early refusal, retaining the canonical FFmpeg write/backup/decoded-audio assertions and adding unchanged alias-target sentinel, zero new target files and unchanged alias-audio/source assertions. No production guard was relaxed and no test was skipped.

Final correction verification: **32 Qt-free Python tests passed** across `test_headless_legacy_import.py` and `test_headless_legacy_startup.py`; **1 real FFmpeg loudness integration test passed**, including its canonical success and aliased-startup negative branches. Added startup tests independently cover both leaf and ancestor aliases. Ruff and focused Pyright pass for the new test. Working files refrozen after this gate correction.


Cross-platform real-core fixtures now canonicalize temporary paths before startup, matching Electron storage. A Linux symlinked TMPDIR reproduced the old Live/offline/review fixture failures; all three pass after realpath conversion. Profiles and baseline workflow fixtures use the same canonical rule. The negative startup tests still require both leaf and ancestor aliases to be rejected before database/settings/root/journal creation. No production guard was relaxed.
