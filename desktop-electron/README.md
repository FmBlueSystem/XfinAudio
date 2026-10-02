# XfinAudio Next: Qt-free migration preview

This is a source-development migration preview, not a signed/released replacement for the installed app. Baseline: `dd15f0dffb9d524169d9559e538e23afb23861a4`. The original Qt application is retained unchanged as rollback.

## Current V8 checkpoint

V8 adds optional language assistance to Library, Prep, Review, saved sets, the editor, Metadata, Live and a synthetic connection probe. It reuses the original interpreters and narrators. Shared preview/disclosure, unchecked per-request consent and a native confirmation protect each request to the fixed Nan Builders endpoint. Native selection records only the credential-file source; key values never enter renderer state, app settings or diagnostics. The original trusted timeout budgets are preserved: Prep 60 seconds, Review 120, connection 10, other surfaces 30.

Requests and cached results are bound to source/settings/credential identity and the exact normalized request/scope. Local Apply preserves hard user controls and cannot save, export, write audio or advance Live by itself. The Metadata narrator omits global lock-priority facts when that state is unavailable, rather than inventing a zero count. Provider testing is offline with dummy files and an injected fake transport only; no real credentials/provider request or actual provider acceptance has been performed. Follow `QA_OPTIONAL_AI_V8.md` for the native fixture matrix.

This remains a development checkpoint. Full original-core parity and distribution are not complete: read-only spectral/danceability/edge completion, detailed generated-review edits/evidence, offline library and saved-set actions, persistent Prep controls, safe legacy-data import and bundled runtime packaging are following work. In particular, a fresh V8 library does not gain spectral profiles, so the color strategies can correctly report unavailable prerequisites. Optional full-library title sharing and inline editing of the AI filter proposal remain more restrictive than the old UI. The later milestone sections below retain their historical validation context.

## Run in an isolated development environment

Requirements: Node.js 24+, Python 3.12 and uv. The eventual desktop distribution must bundle Python; this source preview still needs an explicit development interpreter.

From the repository root:

```sh
uv venv --python 3.12 .venv-headless
uv pip sync --python .venv-headless/bin/python desktop-electron/requirements-headless.txt
cd desktop-electron
npm ci
export XFIN_PYTHON="$(cd .. && pwd)/.venv-headless/bin/python"
export XFIN_DATA_DIR="$(mktemp -d -t xfinaudio-next.XXXXXX)"
npm start
```

XFIN_DATA_DIR isolates the application databases and, before Electron becomes ready, its Chromium profile, session/cache data, logs and crash-dump directory. Its path must be absolute.

The new interpreter contains mutagen, Pydantic and NumPy, with transitive requirements hash-locked. It does not install or import Qt. Do not use `uv sync` at the root for this new application: the legacy app still declares Qt there. On macOS, use a native arm64 Node/Python environment on M1. Do not disable Electron's sandbox to work around a host startup error.

## First workflow

1. Choose a copied music folder (the included `tests/fixtures/music` contains eight synthetic playable silent FLACs)
2. Browse/search/filter parsed metadata
3. Choose from the existing strategy catalog and set optional slot, genre, opening/closing, required and excluded-track controls
4. Compare the real safe, balanced and adventurous variants, then review ordered tracks, readiness, warnings and blockers
5. Explicitly save, list and reopen a playlist
6. Preview original files through one player: play, pause, seek, switch and volume
7. Open Metadatos to review actual missing-field counts, filter the repair worklist, inspect explanations and preview a track. Large worklists page at 100 rows while search covers the full report.

Metadata scanning stays read-only. App-owned databases and root authorizations are written for normal library/playlist work. The Serato screen additionally writes only an explicitly selected crate after preview and native confirmation; validation so far uses disposable fixtures. Loudness tag writing requires its separate scope preview and native confirmation. Optional AI requests require their separate consent/native confirmation; automated validation uses dummy-only fake transport. Spectral completion and Serato database V2 mutation do not run in this V8 preview.

## Tests

```sh
# From repository root, an environment also needs pytest, ruff and pyright to run Python checks
PYTHONPATH=src .venv-headless/bin/python -m pytest --noconftest -q tests/test_headless_backend.py tests/test_headless_protocol.py
# The legacy tests/conftest.py imports Qt, hence --noconftest for isolated headless tests
cd desktop-electron
XFIN_PYTHON="$(cd .. && pwd)/.venv-headless/bin/python" npm test
```

`npm test` compiles strict TypeScript then runs protocol, path/range, lifecycle, renderer helper/player tests. With `XFIN_PYTHON` set, it also runs the actual core subprocess through scan → balanced → save → restart/open → FLAC byte-range serving. Without that variable the integration case is explicitly skipped. Player unit tests mock the browser audio element; they do not prove native audio decoding/output.

## Security and lifecycle

- Sandboxed renderer, context isolation, no Node, no remote content, strict CSP
- One allowlisted preload interface; sender frame/origin checked in main
- No HTTP listener; local assets and authorized opaque-ID audio use custom protocols
- Requests have bounded JSONL frames, IDs and fixed commands; Python logs to stderr
- Single mutation job, explicit cancellation and stale-review IDs; playback resolution remains available during work
- Audio range/HEAD/416 support; no-follow descriptor open and canonical-path/inode/device/size/mtime identity verification
- Normal core shutdown drains or escalates to process termination within six seconds. An active confirmed crate publication is noncancellable and drains first, so safe shutdown can take longer.

## Known limits and next slices

Native macOS arm64 programmatic smoke subsequently passed scanning synthetic tracks and 14 copied real tracks, balanced Prep, review/save/restart/open, muted FLAC play/pause/seek/resume/switch, sandbox-enabled startup and exit 0 shutdown. Human interaction, audible output and long-library stress remain mandatory. The v1 update also passed all 30 Node tests and native revalidation of the isolated profile paths; the prior profile timestamps remained unchanged. The v2 Prep/metadata slice also passed native Studio programmatic checks: all 60 Node tests, all 11 strategies/constraints/variants, metadata 205-track pagination at 100/100/5 rows, keyboard skip-link IPC, muted playback and restart/open. The v2 Studio check also passed on 24 copied real tracks, including restart/order and missing-file recovery; original/copy hashes remained unchanged. human/audible/stress validation remains outstanding. Cloud shell Electron startup was blocked before app code by unavailable DBus sockets; no sandbox changes were made. The cloud browser rejected file URLs. No screenshot or native stability claim is made.

Remaining migration work includes library watcher lifecycle, remaining persistence actions, Live Assistant, settings/loudness behavior, optional provider surfaces, bundled Python, platform packaging/signing and updater/release policy. This slice deliberately leaves those unavailable rather than substituting placeholder algorithms.

The required legacy aggregate release gate was attempted but its fresh Qt dependency installation exhausted temporary disk space. It did not reach the test suite and is not reported as passed. A no-download reuse of the existing legacy environment reached the aggregate suite but exited 137 around half-way. Equivalent fresh-process coverage then completed all 3337 Python tests at 94.29%, with full type/lint/format and release/source-hygiene/check-only packaging checks passing; this does not relabel the monolithic command as passed. Focused Qt-free core tests and the actual subprocess integration passed; see `openspec/changes/electron-qt-free/verify-report.md` for exact evidence.

Review/publish plan: chain independently reviewable backend, host, renderer and packaging changes within the repository's 400-line per-review budget. Nothing has been pushed, merged or released.

## v2 verification checkpoint

The combined Node suite passes 60 tests with both real-core integration cases enabled and no skips. Focused Python/domain checks pass 189 tests, with one explicitly Qt-dependent wrapper check skipped only in the Qt-free environment; the wrapper and related legacy regressions passed separately with Qt. Full Pyright reports 0 errors, locked Ruff lint/format pass. The full v2 fresh-process run passed all 3,398 tests at 94.33% combined coverage, with full type/lint checks green. This is a development checkpoint, not a release gate or live Serato compatibility claim.

## Saved-playlist editor checkpoint (v3)

Saved cards now offer Rename, Duplicate and Edit. The editor supports indexed reorder/removal, honest missing-file markers, explicit Save/Discard and atomic name/order persistence with concurrent-change protection. Bounded offline suggestions use the existing parser and musical assessment: Preview → Apply to draft → Save. Dirty drafts survive navigation; changing sets asks before discarding. Closing with unsaved changes offers continue editing or discard/exit; Cancel keeps the core available. No deletion or export action is added in this slice.

Combined Node verification passes 94 tests with all 3 real-core integrations and no skips. Focused Python verification passes 139 tests plus one explicitly Qt-only skip; the relevant legacy compatibility suite passed separately. Full v3 fresh-process verification passed all 3,439 tests at 94.37% combined coverage, with type/lint/format checks green. Native Studio programmatic testing also passed synthetic and 24-copy editor/preview/apply/save/draft/close-cancel/discard flows; original/copy hashes remained unchanged. Dialog choices were controlled test responses, not human acceptance.


## Serato export checkpoint (v4)

From a reviewed selection or a saved playlist choose **Exportar a Serato**. Pick the existing `_Serato_` folder containing `Subcrates`, choose a crate name, inspect the read-only preview, then select **Exportar a Serato…**. A separate native confirmation shows the exact file/destination, track count and replacement/backup warning. The crate is written directly to the chosen destination. Other export formats are outside this workflow.

- Current review or exact saved order; missing tracks and blocked readiness prevent export. An unsaved editor draft must be saved or discarded first.
- Source, destination lineage, target identity and bytes are bound to an immutable preview. Changes require a fresh preview; no silent regeneration on commit.
- At most 500 track references per export; anchored crate reads/writes are capped at 16 MiB. The original larger saved playlist is never truncated or changed.
- Source tracks and destination must be on the same source volume. Internal macOS/APFS references use `/`; external `/Volumes/<disk>` references retain that disk root. Mixed-volume export fails closed.
- Existing crates receive an exclusive backup. Native no-replace publication protects concurrent arrivals. Overwrite briefly removes the old target name while capturing/verifying it, with its backup retained; recovery copies survive restoration conflicts.
- Linux native exclusive rename has fixture coverage. The Darwin ABI is unit-tested, but native macOS/removable-filesystem execution still requires validation. Unsupported safe publication primitives fail closed.
- Successful receipts can reveal only the verified exported file. Navigation does not lose a completed receipt. Export cannot be cancelled after publication begins, and application shutdown waits for it.
- User-facing transport failures now use Spanish guidance; technical codes/details remain local diagnostics.

All automated writes use temporary `_Serato_` folders, synthetic/copied tracks, and database V2 sentinels. A valid fixture crate does not prove live Serato import compatibility. No live export, signed build, public push, merge or release has occurred.

Source handoffs can be built with `python scripts/create_source_archive.py CHECKOUT OUTPUT.tar.gz` where OUTPUT is outside the checkout. It excludes generated/dependency trees including dependency symlinks, rejects unexpected links/special files/sensitive configuration, and emits deterministic regular-file-only archives.

Final v4 cloud checkpoint: 3,538 Python tests passed in 23 fresh-process batches at 94.29% combined coverage; full type/lint/format, release smoke, source-package hygiene and PyInstaller check-only pass. All 122 Node tests pass with four real-core integrations and no skips. Native v4 Serato verification remains pending; follow `QA_SERATO_V4.md` using temporary fixtures only. This does not mark the original monolithic release command as passed.

## Live guidance checkpoint (v5)

A completely ready current Prep review can open **Abrir guía Live**. The existing scoring helpers are moved byte-for-byte into the neutral application package, with the Qt import facade preserved. Live starts with the exact first track, ranks only the applied pool, preserves the original controls/arc rules and records manual next-track marks. Prelistening is separate and never advances the guide or controls Serato decks. Navigation preserves progress; source changes invalidate it. Core disconnect keeps an explanatory unavailable snapshot and pauses its display timer.

The new aggregate `--coverage-batch-size` option isolates legacy test resources without reducing the suite or coverage floor. The Electron/real-core checks still run separately with `XFIN_PYTHON` explicitly set. Native V5 validation is pending.

V4 subsequently passed programmatic native Studio testing on internal APFS temporary Serato fixtures, including confirmed creation/replacement/readback, cancelled dialogs, stale/missing/blocked sources, safe Spanish operation status and preserved original/copy/database sentinel hashes. Controlled dialogs are not human acceptance, a bridge-delayed publication test is not physical slow-I/O evidence, and removable filesystems/live Serato import remain untested. Some domain warning text remains English.

V5 final cloud checkpoint: 147/147 Node tests with all five real-core integrations enabled; the supported aggregate sharded mode passed all 3,590 Python tests at 94.35% coverage and every other automated gate. Native V5 remains pending. The aggregate retains older MIK evidence; new Electron human/audible/stress acceptance and bundled-platform packaging remain separate work.

## Preferences and library observation checkpoint (v6)

**Preferencias** now saves initial preview volume and read-only library-change observation in the isolated app settings. Save explicitly applies volume; footer changes affect only the current session. Unsaved preferences and playlist edits jointly protect closing. Existing settings fields are preserved, but provider and loudness/tag-write services remain unavailable in this slice rather than starting implicitly.

The library status panel separates last-scan state from observer availability and offers an explicit rescan of previously authorized folders. Observation runs in a bounded native worker, ignores app-owned data and never automatically scans or modifies audio. Generation guards and awaited shutdown prevent stale events from reviving retired watchers. Completed scans publish clean even if watching is unavailable; failed/cancelled scans do not invent a clean snapshot. Linked/oversized/unsupported trees fall back visibly to manual rescan. See `QA_PREFERENCES_WATCH_V6.md` for the exact bounds and native test matrix.

V5 subsequently passed programmatic native Studio validation with synthetic tracks and 24 authorized copies, including Live readiness/history/stale/disconnect/close behavior and baseline editor/playback regression; original/copy/sentinel hashes remained unchanged. Native V6 validation and final automated counts are recorded in its verification report. Human/audible/prolonged acceptance and distributable packaging remain pending.

V6 final cloud checkpoint: all 3,612 Python tests passed at 94.34% coverage and all 10 automated aggregate gates passed; 189/189 Node tests passed with six real-core workflows and no skips. Source/native handoff remains a development preview, not an installed release.

## Loudness checkpoint (v7)

**Sonoridad** restores the original FFmpeg EBU R128 engine, completion/cache service, three settings and format-aware tag writer. The configured target/tolerance now really apply to Prep's loudness policy. In this new runtime, select an explicit scope (at most 500 tracks), inspect its read-only preview and approve a separate native confirmation before analysis and automatic tag/comment writing. There is no second tag-write switch and no silent startup/scan-triggered write from an inherited enabled default.

Changed writes use a descriptor bound to the confirmed source and retain an exact original-byte backup plus a local recovery manifest. The original format writer remains authoritative; no audio transformation is introduced. Cancellation stops pending analysis and waits for a started metadata commit. Partial outcomes and backups remain visible after cancellation; post-write cache/status failure produces a warning rather than hiding the receipt. The recovery button reveals only the isolated app-owned backup folder. A failed partial filesystem save retains recovery bytes but is not described as universal transactional rollback.

Source mode requires trusted FFmpeg on PATH. Engine unavailable/short/unmeasurable/temporary failure states remain explicit. Automated validation uses copied/synthetic fixtures only; see `QA_LOUDNESS_V7.md`. Full backup .bak files contain audio and must not be uploaded with evidence. Optional NaN/provider parity, bundled-platform distribution and human/audible/prolonged acceptance remain pending.

V6 subsequently passed programmatic native Studio verification without source fixes: all 189 Node checks, preferences/recovery/dirty-close flows, real observation/rescan/limits/cancel/drain, original/copy/sentinel hash protection and baseline playback/Live/Serato regressions. Native V7 validation is pending.

V7 final cloud checkpoint:235/235 Node tests, seven real-core workflows, no skips; all 3,702 Python tests in 24 aggregate batches passed at 94.41% coverage and all 10 automated gates passed. Native V7 remains pending.


V8 final cloud checkpoint: **3,859 Python tests, 24 supported aggregate batches, 94.48% coverage and all 10 automated gates passed**. **286 Node tests with eight real-core integrations passed, zero skips**; optional-provider execution is dummy/fake only. The separate Qt-free subset passed 471 tests with two legacy-Qt wrapper skips (both covered by the full aggregate). Native V8 and the bounded following parity/packaging work remain outstanding.


## V9 original-functionality and standalone-runtime work

The bounded functional inventory and deliberate differences are in `MIGRATION_SCOPE.md`.

V9 restores the original read-only profile completion/cohesion policy, deterministic review evidence and generated-set edits, offline Library/saved-set actions, recoverable saved deletion, persistent Prep controls, metadata worklist Serato export and an explicit fresh-profile legacy import. These reuse the original Python engines/helpers. The native fixture matrix is `QA_PARITY_V9.md`; current focused evidence lives in the corresponding `openspec/changes/electron-*` reports. Final aggregate and packaged-runtime evidence must match the source digest recorded with the candidate.

Legacy import is explicit and bounded to a fresh destination. The original installation is retained; credentials and root permissions are not imported, and music requires separate folder authorization. Reports/other DJ export formats are not added. The portable Linux build is documented in `packaging/linux/README.md`; it bundles Python/FFmpeg, and a source-mode/native test alone does not prove a bundled GUI launch.


V8 subsequently passed programmatic native Mac Studio validation: all 286 Node checks, all eight optional-assistance surfaces with fake transport and zero network calls, interruption/hostile-response/restart/FLAC-copy regressions, and unchanged 24 original/copy hashes. No Qt or real credentials were used. This is programmatic evidence; it does not establish actual provider or human/audible acceptance. V9 requires its own matching native validation.
