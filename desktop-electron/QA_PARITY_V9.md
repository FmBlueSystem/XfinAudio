# V9 native fixture validation

Use a freshly materialized source snapshot and isolated native architecture Node/Python environment with the locked Qt-free requirements. Preserve all earlier test/source/data directories and the installed Qt rollback. Never use real credentials, provider traffic, originals, live Serato or the actual old application profile in this matrix. Use disposable generated audio and copied synthetic databases only. A source-mode native pass is separate from the bundled Linux runtime and from human/audible/prolonged acceptance.

## Fixtures and baseline

- Generate at least four distinct non-silent 70-second audio fixtures with BPM/key/energy/genre tags, plus one silent file, one with missing metadata, and one intentionally undecodable file. Include supported container copies where useful. Record SHA256 and mtime before/after every read-only workflow.
- Use a fresh XFIN_DATA_DIR. Confirm profile/cache/log/crash/settings/database paths remain isolated and Qt is absent from the selected Python environment.
- Run strict TypeScript and all Node tests with XFIN_PYTHON explicitly set; no real-core skips. The new actual profile test uses the original analyzers. Do not confuse a generated-profile mock with the actual-engine integration.
- Start a second instance against the same isolated profile and verify it exits without starting another core or changing app data.
- Run baseline Library, Prep variants, saved editor, Live, muted playback, preferences/watch, confirmed loudness and fixture-only Serato regressions. Loudness may write only fresh dedicated copies and must retain original-byte backups/unchanged decoded PCM; do not include audio backups in evidence uploads.

## Read-only profile completion and cohesion

1. A successful scan/rescan first displays metadata, then one spectral → danceability → edge completion sequence. Actual non-silent long fixtures gain all three original profiles and both color strategies produce usable sets. Silent/short/unreadable fixtures remain honestly partial/unavailable; no fabricated values.
2. Profile counts are independent of metadata completeness. Complete metadata with unavailable profiles and incomplete metadata with measured profiles both render without rejecting valid results.
3. Observe bounded progress, cancel during analysis, restart/retry and close. No pending result should persist/publish after acknowledged cancellation; already saved cache remains recoverable. No orphan workers. A successful watch-driven rescan must not leave profile completion permanently paused.
4. Restart and repeat: current profiles reuse the cache; modified/replaced/symlinked files and obsolete versions cannot reuse stale values. Source hashes/mtime remain identical after read-only work.
5. Change spectral cohesion, save, restart and verify its real effect on the original Prep/Live policy. Test revision conflict, dirty-close cancellation, preserving unrelated settings/editor drafts, and no autoplay.

## Offline Library and saved sets

- Without AI enabled/configured, interpret and manually apply genre/BPM/key/energy queries. Exercise sorting and duplicate hiding using the original local behavior, then clear filters. Compare displayed IDs with the exact original helper output.
- Search and compare saved sets locally. Native-cancel a deletion, then confirm removal of a named exact revision. Restart: the app-owned recovery remains available and restores exact order, duplicates and missing references once. Changed snapshots/invalid IDs fail safely. No audio mutation.
- Current Library Complete or Incomplete worklists can be sent to the existing Serato preview. Mixed/all, zero or over500 selections cannot silently broaden/truncate. The current visible filtered IDs across all pages are the export scope.

## Generated review and persistent controls

- Inspect deterministic transition component scores, readiness checks and engine facts independently of AI. Compare replacements without changing the current review. Explicit reorder/remove/backfill reuse original helpers, retain protected constraints and produce new revision-bound readiness.
- Save/export/Live use the exact current reviewed order. Stale review IDs, duplicate/unknown reorder IDs and illegal removal of protected tracks fail.
- Change bytes/metadata/policy after generation: old review save/export and reselecting a cached variant must fail, rather than blessing stale evidence with a new review ID. Test source change during generation too.
- Persist locks/exclusions/genre, restart and verify restoration only for authorized current tracks; missing/unresolved references are disclosed. Preferences/source changes invalidate dependent evidence, and unsaved controls participate in dirty-close behavior.

## Metadata repair worklists to Serato

- Filter missing BPM/key/energy plus search across more than one page. The export callback uses the exact full filtered IDs, at most500. It never silently exports only the current page.
- Preview is read-only and explicitly labels a metadata worklist, not DJ readiness. Select a temporary _Serato_ containing Subcrates, inspect exact tracks/destination, cancel the native confirmation and verify zero writes.
- Confirm one fixture export, parse its crate paths independently, replace it with an exact backup, and verify source/sentinel hashes. Change a source/metadata/destination after preview and require a fresh preview. No database V2 writes or other output formats.

## Explicit legacy import into a fresh profile

- Build a separate synthetic legacy directory with valid tracks/cache, saved sets (including duplicate/missing references), and settings. Never point this test at the user's actual old profile or existing credentials.
- Native selection/preview reads only the selected directory. Cancel produces no active-profile import. Reject symlink/parent swap, oversized/corrupt/unknown schema, active SQLite sidecars and changed source/destination. Include concurrency at prepared-journal and partial-publication boundaries.
- Native confirmation states the old app must be closed/checkpointed, that the source stays unchanged, that only a fresh destination is accepted, and that music roots must be selected again. Confirmed import retains recoverable destination backups and safe source snapshots.
- Only the stated safe preferences are imported. AI credentials/source/enabled state, old root authorization and automatic write/provider behavior are excluded. The selected original source and synthetic audio hashes remain unchanged.
- Require restart before using imported data. After restart, saved sets/cache are present but music stays unauthorized until a separate native folder selection/rescan. Verify importer crash recovery without overwriting conflicting newer work, and never describe a source or destination race as success.

## Evidence and limits

Keep structured test outcomes, sanitized logs, screenshots of actual native confirmation/cancel/error states, and before/after hashes. Do not upload copied music, .bak audio, real databases/settings or credentials. Separate programmatic controlled-dialog checks from human acceptance. No release, signing, public push, original installation replacement, live provider acceptance or live Serato import is implied by this matrix.


The dependency-only freezer validation covers cold/warm real computations in WAV, FLAC, MP3, AAC-M4A, ALAC-M4A and AIFF, a relocated read-only bundle, isolated/hostile inherited cache settings, and unchanged source hashes/mtimes. The final application freeze must independently pass its actual runtime smoke. The scientific-module and PCM-output preflights are required; a version string alone is insufficient.
