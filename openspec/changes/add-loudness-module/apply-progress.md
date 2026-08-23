# Apply Progress: add-loudness-module

## Status

WU1 and WU2 tasks 2.1–2.4 are complete under strict TDD. Pipeline integration remains pending.
The executor did not settle the supplied native runtime token.

## Completed Tasks

- [x] 1.1–1.3, 1.6–1.7 — Loudness port/profile, command/parser, conformance fixtures, and duration floor.
- [x] 1.4 — Capability preflight requires an absolute executable file with execute permission, successful typed probes, an `ebur128` filter entry, and the `true` value of the `peak` option.
- [x] 1.5 — Timeout kills then reaps the owner process; cancellation/shutdown synchronize spawn, registration, kill, and owner reaping.
- [x] 2.1 — Nullable `loudness_profile_json` migration and explicit scan upsert `CASE` preserve an existing payload on ordinary rescans.
- [x] 2.2 — Versioned profile JSON cache checks its own post-write mtime/size against disk, not shared track identity.
- [x] 2.3 — Supported post-tag-write identity refresh atomically updates shared mtime/size without changing sibling profile JSON.
- [x] 2.4 — Typed failures persist/cache on unchanged inputs; explicit force reanalysis bypasses the cache.

## TDD Cycle Evidence

| Tasks | Test file | Layer | Safety net | RED | GREEN | Triangulate | Refactor |
|---|---|---|---|---|---|---|---|
| 1.1–1.3, 1.6–1.7 | `tests/audio/test_loudness.py` | Unit | New module | Missing-module collection failure | 5 passed | Golden, malformed, and short cases | `StrEnum` cleanup |
| 1.4 | `tests/audio/test_loudness.py` | Unit with typed probe fakes | 5 existing tests passed | Non-executable paths, non-zero probes, and unrelated `peak`/`true` text failed against the original preflight | 8 passed in commit `a90056c` | Valid vs invalid executable/probe/output cases | Extracted structured probe helpers |
| 1.5 correction | `tests/audio/test_loudness.py` | Deterministic real-thread process lifecycle | 10 passed in 1.68s | `uv run pytest -q tests/audio/test_loudness.py` → 5 failed, 10 passed: no owner reap, race let cancel/shutdown return early, and probe contract was untyped | Same command → 14 passed in 1.81s | Timeout owner-reap plus both cancel and shutdown race paths | Condition-protected lifecycle registry; focused suite remained green |

## Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test | `uv run pytest -q tests/audio/test_loudness.py` — 14 passed in 1.81s. |
| Static checks | `uv run pyright src/xfinaudio/audio/loudness.py tests/audio/test_loudness.py` — 0 errors, 0 warnings; focused Ruff check and format check passed. |
| Runtime harness | Deterministic probe/process fakes plus real Python threads exercised the factory-registration cancellation race, owner reaping, timeout classification, and process-group kill. No real FFmpeg executable ran. |
| Rollback boundary | Revert commits `a90056c` and this task-1.5 commit together to remove the WU1 runtime boundary without touching WU2+. |

## WU2a Task 2.1 Evidence

| Task | Safety net | RED | GREEN | Refactor |
|---|---|---|---|---|
| 2.1 | `uv run pytest -q tests/test_track_repository.py` → 75 passed in 0.67s | Same command → 2 failed, 75 passed: missing column blocked direct payload seed and current-version migration | Same command → 77 passed in 0.58s | Existing nullable-column migration pattern retained; no `SCHEMA_VERSION` bump. |

| Evidence | Result |
|---|---|
| Focused tests | `uv run pytest -q tests/test_track_repository.py` — 77 passed in 0.58s. |
| Runtime harness | SQLite file integration: seed a profile JSON directly, run `save_scan_results`, then read the same column back. |
| Rollback boundary | Revert the WU2a commit to remove only the nullable column and scan-upsert preservation branch. |

## WU2a Maintainer Budget

The maintainer constrained this objective to **330 text changed lines**, including tests and SDD artifacts, to reserve correction margin. This slice is limited to task 2.1; it deliberately does not load/cache loudness profiles or implement identity, retry, pipeline, tag, strategy, or UI behavior.

## WU2b Tasks 2.2 and 2.4 Evidence

| Tasks | Safety net | RED | GREEN | Refactor |
|---|---|---|---|---|
| 2.2, 2.4 | `uv run pytest -q tests/test_track_repository.py` → 77 passed in 0.62s | Same command → 5 failed, 77 passed: no loudness cache API | Same command → 82 passed in 0.65s | Shared serializer/deserializer keeps malformed JSON fail-closed. |

| Evidence | Result |
|---|---|
| Focused tests | `uv run pytest -q tests/test_track_repository.py` — 82 passed in 0.65s. |
| Runtime harness | SQLite cache tests use a real temporary file, mutate only shared DB identity, and prove profile-owned identity remains decisive. |
| Rollback boundary | Revert the WU2b commit to remove `TrackRecord.loudness_profile` and repository cache behavior without affecting WU2a schema migration. |

## Remaining Tasks

- [ ] WU2 task 2.5: pipeline integration.
- [ ] WU3 target-band filter, strategy, and tag write-back.
- [ ] WU4 settings, UI surface, packaging, and full verification, except completed governance task 4.6.

## Scope Notes

- No user-library audio was touched. All WU1 process behavior is fixture/fake driven.

## WU2c Task 2.3 Evidence

| Task | Safety net | RED | GREEN | Refactor |
|---|---|---|---|---|
| 2.3 | `uv run pytest -q tests/test_track_repository.py` → 82 passed in 0.73s | Same command → 5 failed, 82 passed in 0.72s: the post-tag identity API was absent | Same command → 87 passed in 0.64s | Kept one supported-suffix guard and one atomic SQLite `UPDATE`; no profile serializer changes. |

| Evidence | Result |
|---|---|
| Focused tests | `uv run pytest -q tests/test_track_repository.py` — 87 passed in 0.64s. |
| Runtime harness | Temporary MP3, FLAC, WAV, and AIFF-named files simulate a metadata-only size/mtime change; no tags are written. |
| Rollback boundary | Revert the WU2c commit to remove only the post-metadata identity refresh helper and its regression coverage. |

## WU2d Task 2.5 Core Evidence

| Task slice | Safety net | RED | GREEN |
|---|---|---|---|
| Headless core | New focused service test | Collection failed: `ModuleNotFoundError: xfinaudio.audio.loudness_completion` | `uv run pytest -q tests/audio/test_loudness_completion.py` — 4 passed in 0.30s. |

The core uses a fixed two-worker cap for external-drive FFmpeg decoding, replays valid cache entries, fresh-stamps profiles after analysis (no tag write exists yet), and directly persists every result. Task 2.5 remains unchecked until Qt/controller/runtime wiring is complete.

## Authorized Governance Reorder (4.6)

- [x] 4.6 The repository rules and README/CONTRIBUTING English/Spanish sections state that scanning remains read-only except for explicit loudness-tag writing. No WU3 behavior is implemented here.

## WU1 Self-Verification — HEAD `202f6fc`

Read-only self-verification completed on 2026-08-22. All requested WU1 gates passed in order; coverage and the release gate were intentionally not run.

| Command | Exit | Pytest/tool result | Wall time | Exact combined-output SHA-256 |
|---|---:|---|---:|---|
| `uv run pytest -q tests/audio/test_loudness.py` | 0 | 14 passed in 1.81s | 3.413s | `sha256:7289061d73e890a291aae88043005e2f17f001fce8381fc6cc7840586dfca78c` |
| `uv run pytest -q` | 0 | 1706 passed, 266 warnings in 32.00s | 35.190s | `sha256:ab3c020f50be511745b388161ef1084af6c3aa26ab2499ac23a6a58fc6a1e449` |
| `uv run pyright src tests` | 0 | 0 errors, 0 warnings, 0 informations | 5.244s | `sha256:3c1a00ce86bcdce1ef7ba97d18d9c5b4e7026f49a5dc61a23382ed7345e02316` |
| `uv run ruff check .` | 0 | All checks passed | 0.115s | `sha256:82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| `uv run ruff format --check .` | 0 | 290 files already formatted | 0.054s | `sha256:aed20c5cdfe9f925fe3d0e35cc2b37455ed39da2dab16a5441a0d6530c2e51af` |

Verification file-drift audit:

- `uv run` transiently changed only the editable-project version in `uv.lock` from 1.8.0 to 1.8.2; the verifier restored that version-only drift to HEAD.
- `docs/reviews/loudness-module-review.md` remained untracked and byte-identical at `sha256:cca5dfd5a0111d59c5280fee9913fbcb40badf6f9c4ac2603b772a19e0e0fdb9`.
- No source or test file changed during self-verification, and project-root `build/` and `dist/` remained absent.

## Native Runtime Status After WU1

Settlement recorded the WU1 evidence as passed but returned `maintainer_decision`: the
fresh-context correction made the final WU1b candidate 560 changed lines against the native
400-line objective, although the implementation and correction commits are independently
303 and 399 changed text lines. Further runtime work is stopped at ledger revision
`sha256:d941ab0d243c9804d1f79fc3aa845bc725019a2f34af87a20dfcad2f139718c6` pending the exact
maintainer reset documented in `IMPLEMENTATION-NOTES.md`.

## WU2e Task 2.5 Lifecycle Evidence

- RED: `uv run pytest -q tests/test_loudness_completion_stage.py` failed at collection because the generic completion stage did not exist.
- GREEN: `uv run pytest -q tests/test_loudness_completion_stage.py tests/audio/test_loudness_completion.py` — 6 passed in 0.66s.
- Generic Qt lifecycle wiring follows edge completion, applies results immutably, and supplies selected → recommendation → visible priorities. Task 2.5 remains unchecked: runtime FFmpeg composition is WU4 scope.

## WU2f Task 2.5 Runtime Composition Evidence

- RED: `uv run pytest -q tests/test_loudness_runtime.py` failed at collection because the runtime resolver was absent.
- GREEN: `uv run pytest -q tests/test_loudness_runtime.py tests/test_loudness_completion_stage.py tests/audio/test_loudness.py` — 21 passed in 2.03s.
- The controller receives a preflighted service when available; frozen mode never searches PATH. Task 2.5 is complete. WU4.5 still owns binary bundling, UPX exclusion, pinning, and license inventory.

## WU2 Self-Verification — HEAD `7a0a55e`

All requested gates passed on 2026-08-22 in order (exact combined stdout/stderr hashes):

- Focused WU2 suite: 112 passed in 3.01s; wall 3.963s; `sha256:249bc13b8c82a0b79aae798e1f3868613adecfa95cf919bf3f4ddc83fa7148e9`.
- Full pytest: 1729 passed, 261 warnings in 51.34s; wall 54.471s; `sha256:c590de63340a84073e06d55020ca65fbfdd421123a6ffe54e5aa630a8c5dd4cc`.
- Pyright: 0 errors, 0 warnings, 0 informations; wall 5.087s; `sha256:3c1a00ce86bcdce1ef7ba97d18d9c5b4e7026f49a5dc61a23382ed7345e02316`.
- Ruff check: passed; wall 0.104s; `sha256:82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18`.
- Ruff format check: 296 files already formatted; wall 0.052s; `sha256:ba046a223e9f43762cca9c846332de658a26517c9939c3d67c012a2d214b899f`.
- Drift: restored the sole transient `uv.lock` editable-version change (1.8.0 → 1.8.2); review doc remained byte-identical at `sha256:cca5dfd5a0111d59c5280fee9913fbcb40badf6f9c4ac2603b772a19e0e0fdb9`; no source/tests changed; root `build/` and `dist/` remained absent.

## WU3a Tasks 3.1–3.2 Evidence

- RED: `uv run pytest -q tests/test_playlist_service.py tests/test_playlist_strategies.py tests/test_application_strategy_catalog.py` failed at collection because `loudness_policy` did not exist.
- GREEN: same command — 239 passed in 0.92s; focused pyright and Ruff passed.
- Consistent Loudness filters only numeric `measured` profiles; coverage warnings report evaluated profiles and exempt tracks without claiming partial output is matched.


## WU3b Task 3.3 Evidence

| Task | RED | GREEN | Refactor |
|---|---|---|---|
| 3.3 | `uv run pytest -q tests/audio/test_loudness_tags.py` — collection failed: `xfinaudio.audio.loudness_tags` missing | Same command — 9 passed | Extracted one formatter and per-family idempotence helpers |

| Evidence | Result |
|---|---|
| Focused tests | 9 deterministic fake-tag tests; no audio files opened or saved. |
| Runtime harness | N/A — the injectable loader/saver isolates this codec; WU3c owns live write ordering. |
| Rollback boundary | Revert the tag codec and its tests without changing analysis, persistence, or pipeline behavior. |


## WU3c Task 3.4 Evidence

| Task | RED | GREEN | Refactor |
|---|---|---|---|
| 3.4 | `uv run pytest -q tests/audio/test_loudness_completion.py tests/test_loudness_runtime.py` — 4 failed: no tag-writer seam | Same command — 11 passed | Kept one failure/profile helper and one identity snapshot helper |

| Evidence | Result |
|---|---|
| Focused tests | Deterministic writer/repository fakes prove analyze → write → post-write stamp → sibling refresh → persist, cache no-write, and failure recovery. |
| Runtime harness | N/A — injected fakes exercise the runtime composition boundary without user audio or mutagen writes. |
| Rollback boundary | Revert the completion ordering, port addition, and focused regressions without changing the codec or cache format. |


## WU3d Task 3.5 Evidence

| Task | RED | GREEN | Refactor |
|---|---|---|---|
| 3.5 | `uv run pytest -q tests/test_loudness_tag_recovery.py` — collection failed: recovery parser absent | Focused scan/repository/tag suite — 135 passed, 30 warnings | Kept recovery in the codec boundary; scan retains no extra raw metadata. |

| Evidence | Result |
|---|---|
| Capability map | MP3/FLAC/WAV/AIFF recover only app-owned v1 structured tags; M4A and unknown suffixes are unsupported. |
| DB precedence | Scan-upsert writes recovered JSON only when the stored JSON is NULL; an existing DB profile wins. |
| Rollback boundary | Revert parser, scan attachment, and nullable-row CASE without changing write-back ordering. |

## WU3 Self-Verification — HEAD `f4bebe5`

- History: the first full-suite RED was the stale 10-vs-11 strategy count; `b155d39` corrected and behavior-pinned it. Later full runs completed all tests but exited 134 with a QThread teardown message; `f4bebe5` hardened lifecycle ownership/reaping. A separate 2h47m pytest process was then terminated. Subsequent green runs correlate with that cleanup but do not prove a thread root cause.
- Focused WU3: 386 passed, 30 warnings in 4.28s; wall 5.346s; `sha256:8b672bcb479232a4d698d74b8f7ec5d7995db51abc38cc484ab5b6040b1d4717`.
- Full pytest: 1762 passed, 264 warnings in 52.29s; wall 55.444s; exit 0; `sha256:e1fba8a18b6c073f9d8ffd3732ed083cd5f8dccf2a0d8ce9f590311213585723`.
- Pyright: 0 errors/warnings/informations; wall 5.281s; `sha256:3c1a00ce86bcdce1ef7ba97d18d9c5b4e7026f49a5dc61a23382ed7345e02316`; Ruff check passed in 0.101s (`sha256:82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18`); Ruff format confirmed 300 files in 0.053s (`sha256:f5e0fe29dfc2d201142550a21657ce32f991da5c51e48495bf92d526b257e2c7`).
- Drift: restored sole transient `uv.lock` version change; review doc remained `sha256:cca5dfd5a0111d59c5280fee9913fbcb40badf6f9c4ac2603b772a19e0e0fdb9`; no source/tests changed; root `build/` and `dist/` absent.

## WU4a Task 4.1 Settings-model foundation (partial)

Task 4.1 remains unchecked: settings UI, runtime scheduling, and translations are intentionally deferred to later WU4 slices.

| Task slice | Safety net | RED | GREEN | Refactor |
|---|---|---|---|---|
| Frozen loudness settings and v1 persistence | `uv run pytest -q tests/test_settings.py tests/test_settings_repository.py` — 17 passed | Same command — collection failed: `ImportError: cannot import name 'LoudnessSettings'` | `uv run pytest -q tests/test_settings.py tests/test_settings_repository.py` — 24 passed in 0.30s | Reused strategy-policy defaults instead of duplicating `−10.0` and `2.0`. |

| Evidence | Result |
|---|---|
| Focused type/lint/format | `uv run pyright src/xfinaudio/config/settings.py tests/test_settings.py tests/test_settings_repository.py` — 0 errors; `uv run ruff check …` — passed; `uv run ruff format --check …` — 3 files already formatted. |
| Runtime harness | N/A — this is a frozen Pydantic model and JSON repository contract with no runtime process boundary. |
| Rollback boundary | Revert `LoudnessSettings`, its AppSettings field/export, tests, and WU4a notes; no UI, scheduler, tag-write, or schema behavior is included. |

## WU4b Task 4.1 UI and runtime wiring (partial)

Task 4.1 remains unchecked pending WU4.4 translation catalog updates.

| Task | Safety net | RED | GREEN | Refactor |
|---|---|---|---|---|
| 4.1 UI, policy, scheduling | 23 focused tests passed | 36 tests: 6 failed (missing controls, workflow override, current-band forwarding, disabled scheduling, Prep forwarding) | 244 passed in 2.65s | Reused one `LoudnessBand` value across desktop and Prep boundaries. |

| Evidence | Result |
|---|---|
| Focused command | `uv run pytest -q tests/test_settings_dialog.py tests/test_settings_controller.py tests/test_playlist_workflow.py tests/test_recommendation_service_state.py tests/test_loudness_completion_stage.py tests/test_application_prep_copilot.py tests/test_prep_copilot.py tests/test_prep_copilot_controller.py tests/test_playlist_service.py` — 244 passed. |
| Type/lint/format | `uv run pyright src tests` — 0 errors; `uv run ruff check .` — passed; `uv run ruff format --check .` — 300 files already formatted. |
| Runtime harness | N/A — deterministic Qt/test-double seams prove scheduling without running FFmpeg or touching audio. |
| Rollback | Revert this UI/policy/scheduling wiring and tests; WU4a model, WU3 tag writer, cached profiles, and translations remain independent. |

## WU4c Task 4.2 Completion progress

| Task | RED | GREEN | Refactor |
|---|---|---|---|
| 4.2 | `uv run pytest -q tests/test_app_state_transitions.py tests/test_loudness_completion_stage.py tests/test_library_screen.py` — collection failed: missing `apply_loudness_completion_finished` | `uv run pytest -q tests/test_app_state_transitions.py tests/test_loudness_completion_stage.py tests/test_library_screen.py tests/test_library_controller.py` — 70 passed | Reused immutable AppState transitions and the existing library progress bar. |

| Evidence | Result |
|---|---|
| Stage lifecycle | Start sets total from all completion records; stage-scoped results apply profiles and increment once; stale results/finishes cannot change progress; cancel, finish, and shutdown reset it. |
| UI | Existing progress label/bar now renders `Analyzing loudness {0:,}/{1:,}` without a new worker or table column. WU4.4 owns translation catalogs. |
| Focused type/lint/format | `uv run pyright src tests` — 0 errors; `uv run ruff check .` — passed; `uv run ruff format --check .` — 300 files already formatted. |

## WU4d Task 4.3 Selected-track loudness detail

| Task | RED | GREEN | Refactor |
|---|---|---|---|
| 4.3 | `uv run pytest -q tests/test_library_screen.py tests/test_library_controller.py` — 6 failed: detail API/widgets absent | `uv run pytest -q tests/test_library_screen.py tests/test_library_controller.py tests/test_loudness_completion_stage.py` — 49 passed | Applied Ruff formatting after the focused green run. |

| Evidence | Result |
|---|---|
| UI behavior | A selection-bound, accessible pane reports one-decimal LUFS/LRA/dBTP, missing/non-measured/too-short states, and exact true-peak boundaries. Profile completion refreshes the selected pane; clearing selection hides it. |
| Table contract | The existing 12-column library table is unchanged. |
| Focused type/lint/format | `uv run pyright src tests` — 0 errors; `uv run ruff check .` — passed; `uv run ruff format --check .` — 300 files already formatted. |

## WU4e Tasks 4.1 and 4.4 Localization completion

| Task | RED | GREEN | Refactor |
|---|---|---|---|
| 4.1, 4.4 | `uv run pytest -q tests/test_loudness_translations.py` — 2 failed: `Consistent Loudness` absent from TS catalogs | `uv run pytest -q tests/test_loudness_translations.py tests/test_build_view_model.py tests/test_settings_dialog.py tests/test_library_screen.py` — 66 passed | Replaced mixin/builder `tr` calls with explicit `LibraryScreen` translation context. |

| Evidence | Result |
|---|---|
| Catalogs | Finished source-equivalent English and neutral Spanish entries cover strategy, settings, progress, details, badges, and missing states in both TS/QM pairs. Placeholder strings are byte-identical between source and translation. |
| Churn control | Full `update_translations.py` exposed 245 unrelated stale entries; its TS/QM output was reverted, then the affected source catalog was merged and both QM files regenerated with `pyside6-lrelease`. |
| Focused type/lint/format | `uv run pyright src tests` — 0 errors; `uv run ruff check .` — passed; `uv run ruff format --check .` — 301 files already formatted. |

## WU4g Task 4.5 Packaging integration

| Task | Safety net | RED | GREEN | Refactor |
|---|---|---|---|---|
| 4.5 | `uv run pytest -q tests/test_pyinstaller_packaging.py tests/test_open_source_license_docs.py tests/test_third_party_license_inventory.py` — 31 passed | Packaging contract test failed: no bundled FFmpeg declaration | Same command — 32 passed | Kept validation in the PyInstaller spec so packaging fails before analysis. |

| Evidence | Result |
|---|---|
| Bundle contract | Source-built `packaging/ffmpeg/ffmpeg` is validated as executable universal2 with ebur128 true peak, bundled at root, and excluded from UPX. |
| Provenance | Inventory pins FFmpeg 7.1.1, official source/checksum, LGPL configuration, source rebuild command, macOS target, and `_MEIPASS/ffmpeg` location. |
| Runtime harness | N/A — inspection-based fake-free packaging contract; no FFmpeg binary or source build is run in tests. |
| Rollback boundary | Revert spec, inventory/strategy, task, and test changes; the WU4f source builder remains independently usable. |

### WU4g correction

- RED: `uv run pytest -q tests/test_pyinstaller_packaging.py` — 2 failed, 16 passed: missing exact build-surface provenance and version rejection.
- GREEN: `uv run pytest -q tests/test_pyinstaller_packaging.py tests/test_open_source_license_docs.py tests/test_third_party_license_inventory.py` — 33 passed.
- Added a fake executable/tool validator regression for rejected non-7.1.1 output; the inventory now mirrors every enabled/disabled build flag and defines corresponding-source retention or durable-offer terms.

## WU4 Final Verification — spectral QThread teardown remediation

| Stage | Evidence |
|---|---|
| RED | `uv run pytest -q tests/test_main_window.py -k widget_scan_guard` — 1 failed: the stale guard still allowed `SpectralCompletionWorker.start()` to run. |
| GREEN | `uv run pytest -q tests/test_main_window.py -k 'widget_scan_guard or starts_spectral_completion or repeated_spectral_worker'` — 3 passed; controller/lifecycle suites — 30 passed; main-window/scan suite — 144 passed. |
| Stability | `uv run pytest -q` twice from clean processes — 1797 passed, 45 warnings in 60.06s and 54.62s, both exit 0 without a QThread teardown abort. |

The test-wide guard had remained attached to the legacy `MainWindow._start_spectral_completion_worker`, while scan completion now calls `LibraryController.start_spectral_completion_worker` directly. The guard now substitutes only the spectral QThread factory with a signal-compatible fake, preserving controller state transitions; explicit lifecycle tests opt in to the real worker. Rollback: revert this guard/test change.

### Final verification coverage precision correction

- RED: `uv run pytest -q tests/test_dependency_bounds.py -k coverage_report_uses_two_decimal_precision` — 1 failed (`KeyError: 'precision'`).
- GREEN: focused contract test passed; `uv run pytest --cov --cov-fail-under=91.14 -q` — 1798 passed, 45 warnings, 91.18%, exit 0.
- Rollback: revert `tool.coverage.report.precision` and its configuration contract test.
