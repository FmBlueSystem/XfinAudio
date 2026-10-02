# V8 optional-AI native macOS QA

Scope: the eight migrated optional-AI surfaces and their native dialog/IPC lifecycle. Use the final corrected source snapshot. This checklist does not authorize a release, real provider traffic, real credential inspection, writes to original music, or live Serato writes.

## Mandatory fixture-only setup

1. Use native arm64 Python/Node/Electron on macOS, with sandbox enabled. Set an absolute, new `XFIN_DATA_DIR`; confirm Chromium profile/session/log/crash paths and app databases are beneath it. Do not launch against the installed application's profile.
2. Copy only the eight synthetic silent FLAC fixtures into a disposable music folder. Create one extra copied fixture with a missing key tag for Metadata. Prepare two saved fixture sets plus one editor session and one ready Live session. No originals are needed. Hash the fixtures and any dummy Serato sentinels before/after.
3. Create a dummy-only credential file containing `NAN_API_KEY=dummy-test-only`. Do not open, search, copy, or inspect any existing credential file, environment secret, keychain entry or installed-app settings.
4. Before the first request, inject a deterministic fake `backend.optional_ai.transport` in a QA-only launch harness, modeled on `desktop-electron/tests/optional-ai.integration.test.mjs`. Block real `nan_client._urlopen`, urllib opener/urlopen, and Python socket connections with throwing stubs. Do not run provider-enabled UI requests unless the fake injection and network blocks are verified. `XFIN_PYTHON` may point to the isolated QA launcher; it must honor the app's data-directory arguments.
5. Keep the fake request log local and sanitized: surface, fixed recipient, request-body categories/count and timing only; never serialize Authorization headers. Assert the synthetic Authorization value in memory. The fake must never forward requests. The actual app passes the fixed Nan HTTPS URL even though the fake handles it locally.

## Native checks

- Baseline launch → scan → local Prep → save/reopen works with no provider requests, no credential reads, no request log entries and no Qt import. The non-AI core startup/export paths also retain their provider-import firewall. Confirm normal close/restart.
- Opening AI status/settings does not read the dummy file contents or invoke transport. Disabled/unconfigured states are truthful. File chooser Cancel retains previous settings. Selecting the dummy file shows only its basename, never its absolute path or contents. Enable/save affects only the selected AI setting.
- Native picker missing/deleted/inaccessible/symlink/oversized file cases fail safely. Include a race deleting a dummy selection before completion. Inspect renderer console/IPC rejection for absence of absolute credential path, dummy token and raw filesystem diagnostics.
- For every surface: prepare shows the fixed recipient and correct disclosure, with unchecked consent; neither prepare nor consent alone sends. Native Cancel/default Escape sends zero requests. Native affirmative sends exactly once. Repeated clicks do not duplicate transport. No consent survives new request, surface, context or settings changes.

### Eight-surface success matrix

1. Library: fake `{"genre":"House","bpm_min":120}` → visible proposal → Apply filters display only; Clear restores full display. The engine library and saved playlists are unchanged. Confirm known paths are absent from the fake body.
2. Prep: fake `{"name":"Fixture warmup","strategy":"warmup","target_track_count":4}` → Apply fills local fields only. No generation until its separate action. Preselect opening/closing/required/excluded tracks; propose different boundary titles and verify local boundaries win, required/excluded selections remain, and conflicting merged controls fail without partially changing the form.
3. Editor: fake `{"operation":"shorten_tracks","target":2}` → AI Apply fills the local request only. The separate local preview and explicit save remain required. Opening the saved set before Save still shows its original order/count.
4. Saved sets: fake `{"action":"compare","selected_ids":["s0","s1"]}` → Apply yields local comparison/selection only. Fake body has anonymous IDs/aggregates, no saved names, paths or track titles. Test empty Find and explicit scope when the collection exceeds 200.
5. Review: plain short fake narrative → commentary only, no Apply. Confirm only the disclosed ordered titles/artists, musical metadata, transition/readiness facts are sent; no paths/audio. Review order/readiness/saveability stay unchanged.
6. Metadata: fake `{"commentary":"Falta tonalidad en una pista de prueba.","fact_ids":["m0"]}` → commentary only. Fake body has counts only, no titles/artists/paths. The locked-gap count is omitted because there is no authoritative lock selection; disclosure states that lock priority is unavailable. Verify no tag writes; a fully complete library has no gap explanation to prepare.
7. Live: fake `{"commentary":"La candidata c0 es la primera opción local.","fact_ids":["c0"]}` → commentary only. Body has anonymous ranks/scores, absolute BPM/energy gaps and readiness. No rank, played-mark or playback changes. Advance/refresh invalidates prior consent/results.
8. Connection: fake `OK` → synthetic result only. No library content is sent. Display explicitly says connection selection is not validation; a previous fake result must not masquerade as actual provider acceptance.

## Interrupted and hostile-result checks

- Delay the fake response. Cancel during native confirmation, during transport, navigate away, change fixture source via the watcher, and close/disconnect the core. Late responses never reappear or become applicable. The UI states already-sent data cannot be recalled.
- Change dummy credential contents, replace the dummy file or parent, change app preferences, edit the request, or change the underlying review/editor/Live session between prepare/run/apply. Require a fresh preview/consent; transport is not reached for pre-run stale cases.
- Fake invalid JSON, unsupported fields/IDs, incorrect recipient, oversized response (>1 MiB), path-bearing structured output, duplicate result IDs/keys, HTML-looking commentary, timeout and errors containing dummy path/token. Confirm the trusted budgets are Prep 60s, Review 120s, connection 10s and 30s otherwise; reject any renderer-supplied timeout. Invalid output yields a safe error and no local action; displayed external text stays plain text.
- Test 2000-character request boundary, too-large genre vocabulary and 200/201 saved scopes. Confirm the 64 KiB request cap rejects locally before fake transport, without reading beyond the 64 KiB credential limit.
- Dirty AI enablement joins close protection; navigation retains the draft. Discard/refresh resolve revision conflicts. Restart retains nonsecret source selection/settings but no preview/result/consent. Clearing the source does not rewrite/delete the credential file.
- Finish with identical fixture/sentinel hashes, no writes outside the isolated profile, zero real-network attempts and a request count matching approved fake requests. Keep screenshots of real macOS picker/confirmation/cancel/error states and separate programmatic checks from human/audible acceptance.

## Current evidence and known limits

Final cloud checkpoint: 3,859 Python tests in 24 aggregate batches at 94.48% coverage and all 10 automated gates passed. TypeScript and 286 Node tests passed with all eight real-core workflows and zero skips; optional AI used injected fake transport only. The separate Qt-free subset passed 471 tests with two legacy-Qt wrapper skips, covered in the full aggregate. These results do not establish native macOS acceptance, live provider compatibility, audible playback or long-library stress. Native fixture execution is next.

Parity observations still requiring an explicit product/testing decision:

- Original Prep 60s and Review 120s budgets are restored by the staged correction, bounded by trusted surface policy. Fake transport still cannot establish real-provider latency compatibility.
- Optional sharing of full track titles in the original Prep UI is absent: new Prep always uses `include_track_titles=False` (`ai_execution.py:42`). Typed boundary titles can still resolve locally. Do not describe full title-sharing parity.
- Metadata has no equivalent authoritative global lock input. The staged correction omits the unsupported locked-gap fact and says that lock priority is unavailable; it does not restore the original Qt global locked-repair workflow.
- Library suggestions are a read-only JSON proposal plus Apply (`optional-ai-view.ts:63–65`); original Qt exposed editable filter fields before Apply (`desktop/optional_ai_surfaces.py:55–62`). The safe effect is present, but inline filter-editing UX differs.
- The staged cache correction rejects old completed IDs after a changed normalized request/surface/scope, invalid preparation or switch-back; history is retained only for an identical immutable reference. The existing cache test covers repeated identical requests, not different requests.

## Staged correction handoff

Before native execution, integrate `xfinaudio-v8-ai-final-corrections.patch` and rerun final gates. It applies cleanly to V8 and V9 and changes 16 files (213 additions, 13 deletions). The isolated staged source passed 235 focused Python/domain tests and 7 native-host Node tests, with Ruff/type checks clean. Canonical copies were not edited while the prior aggregate was running.
