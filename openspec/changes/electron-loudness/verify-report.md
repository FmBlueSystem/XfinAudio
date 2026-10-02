# V7 cloud verification — 2026-10-01

## Final result

- Supported aggregate release gate exited 0: all 3,702 Python tests passed in 24 fresh whole-file batches; combined coverage 94.41% under the unchanged project floor. All 10 automated gates passed, including exact collection/execution evidence, type/lint/format, publication/source hygiene and PyInstaller check-only.
- Strict TypeScript build plus 235 Node tests passed with zero skips/failures. All seven real Qt-free Python-core workflows ran, including actual FFmpeg loudness measurement and tag writing on owned synthetic audio.
- Real 65-second synthetic FLAC: finite complete loudness profile, original-byte backup and recovery manifest, decoded PCM SHA256 unchanged before/after, source fixture unchanged, cache replay without another backup.
- Actual descriptor-based FLAC/WAV/AAC-M4A/ALAC-M4A tag writes and unchanged-repeat idempotence pass. These format tests use supplied complete unit-test profiles; the separate FLAC integration obtains its measurements from actual FFmpeg.

Development FFmpeg: 7.1.5-0+deb13u1 from the existing /usr/bin installation. Distribution pin/provenance remains separate packaging work.

## Requirements and regressions

- Original settings/policy: test_headless_loudness_settings.py covers 45 settings/planner cases. Shared locks/revisions/recovery preserve unrelated fields; original single enabled setting and LoudnessBand reach both candidate routes and Prep generation.
- Scope and engine: test_headless_loudness.py covers read-only status/preview, native-only confirmation, bounded known identities, stale settings/source/scan/scanner identity, truthful missing/failed engines, historical-profile invalidation, cache/force behavior and original completion/tag pipeline.
- Write boundary: test_headless_loudness_write.py covers exact backups/manifests, canonical descriptor identity, changed/symlinked parents/leaves, replacement after backup, unsupported/incomplete profiles, retained originals after simulated partial-save failure, and real supported container handling.
- Lifecycle:13 dedicated checks in test_headless_loudness_lifecycle.py plus original audio-completion/protocol regressions. A reproduced server-lock/commit-progress deadlock is fixed by cancellation marking under lock and drainage outside it. Hooks invoke once, retirement is synchronized and one failed hook cannot skip remaining drainage/join/shutdown. Repository identity reads include empty/missing and 1,803-path chunking.
- Host: loudness-host.test.mjs proves no write on native refusal, no renderer confirmation flags/paths/commands, cancellation during pending confirmation, and close waiting for actual commit/run completion. Fixed backup-directory reveal rejects redirect/symlink targets.
- Observer: native-watch.test.mjs exercises actual worker notifications, exact-path owned-write suppression, expiry and preservation of unrelated-file events. Suppression uses only main/core-scoped identities; no renderer paths.
- Renderer: explicit settings/scope/review/run/force, pagination 100, max 500 selection, dirty-close aggregation, no autoplay, cancellation/disconnect/stale-context receipts, warning-state behavior and recovery-folder empty/legacy-host states are tested.
- Post-write cache/status failures still return mutation/backup counts plus safe warnings. No claim of universal physical-filesystem rollback is made; original bytes remain available for recovery.

## Scope and remaining validation

All automated audio mutations occurred on newly created copies/synthetic fixtures. No original user audio, V6 native baseline, live Serato, provider credential source or external provider request was touched. Source remains unpublished; no merge, installed-app replacement, signing or release was performed.

Native V7 is pending; follow QA_LOUDNESS_V7.md with fresh copies and keep .bak audio local. Actual cloud Electron is still blocked before app code by host DBus; Node/worker/DOM checks are not claimed as a cloud Electron UI run. Controlled publication delays do not prove physical slow/removable-I/O behavior. The aggregate's inherited older Mixed In Key completion label does not establish Electron human/audible/prolonged acceptance.

Optional NaN/provider parity, large-library UI performance, bundled Python/FFmpeg and platform application validation remain subsequent work. The new runtime intentionally requires exact-scope preview/native confirmation before its coupled analysis/tag writing; inherited enabled defaults do not automatically mutate a scanned library.
