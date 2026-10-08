# Verify report — review remediation (2026-10-07)

## Environment

| Item | Value |
|---|---|
| Repository | `/Users/freddymolina/Desktop/XfinAudio/repo-worktrees/ai-playlist-improvement` |
| Branch | `feat/ai-playlist-improvement` |
| HEAD at review start | `3172b4f` "chore(release): prepare 2.3.0 source candidate" |
| Commits created | nine local work-unit commits `3172b4f..HEAD` on `feat/ai-playlist-improvement` (`70d6c0a`, `bb29fac`, `8d18125`, `ad593f4`, `3416410`, `7e0b2e3`, `296cf09`, `95564bd`, plus this change-record commit) |
| Push / tag / merge created | none — every commit is local |
| Date | 2026-10-07 |
| Toolchain | Python 3.12.11, Node 22.22.3 for `npm test`, Electron 44.5.1 |

## Full gate

```bash
UV_OFFLINE=1 uv run python scripts/release_gate_check.py --run \
  --report-json /tmp/xfinaudio-release-gate-report.json
```

- Exit code `0`. Report `overall_status: passed`, `mode: run`.
- All nine gates `passed`: tests and coverage, type-check (`pyright src tests`, 0 errors), lint
  (`ruff check .`), format (`ruff format --check .`, 315 files formatted), release readiness
  smoke, open-source publication docs, publication artifact hygiene, source package hygiene,
  root artifact hygiene.
- `2822 passed, 2 warnings in 91.42s`; coverage `91.83%` against the floor `89` configured in
  `pyproject.toml`. No `--cov-fail-under` was passed on any command line. This is the final
  run, taken after the freezer-lock regeneration and the documentation edits that followed it;
  the earlier green run of this same command reported `2819 passed` before the three new lock
  guards existed.
- Manual gate remains `real Mixed In Key audio QA`; limitation recorded by the report:
  automated tests and fixtures cannot prove it.

Five runs happened in this phase: the first failed on two license-inventory guards, the second
on one `E501`, the third and fourth passed at `2819 passed` (the fourth re-confirmed the tree
after `docs/release-candidate-evidence.md` was regenerated), and this fifth one is the final
gate of record at `2822 passed`. A further run was required because the freezer lock is a
tracked file: changing it invalidated every earlier green result, and a gate result belongs to
the content it actually ran on.

## Requirement evidence

| Requirement | Evidence | Result |
|---|---|---|
| R1 export containment | `tests/test_playlist_file_export.py` (15) | pass |
| R2 in-flight request immutability | `desktop-electron/tests/optional-ai.test.mjs` (34) + `optional-ai-view.test.mjs` (17), in the 519-test Node run | pass |
| R3 headless lock match | `tests/test_headless_requirements_lock_drift.py` (8, three of them over the compiled freezer lock) | pass |
| R4 documentation truth | `tests/test_documentation_freshness.py` (11), `tests/test_sdd_config_matches_project.py` (9), `tests/test_publish_workflow_gates.py` (21), plus the license/public-doc suites | pass |
| R5 discarded-failure observability | `tests/test_swallowed_exception_observability.py` (8) | pass |
| R6 SDD config and skill truth | `tests/test_sdd_config_matches_project.py`, `tests/test_release_gate_check.py` | pass |
| R7 no Qt residue | translation/pyproject guards, workflow guards, `tests/test_ai_connection_test.py` (3) | pass |
| R8 real-core improvement save | `desktop-electron/tests/editor-improvement.integration.test.mjs` (1, ran, not skipped) | pass |

Focused re-run of every document and lock consumer after the evidence regeneration:

```bash
uv run pytest -q tests/test_non_audio_release_gates_workflow.py tests/test_open_source_license_docs.py \
  tests/test_release_gate_check.py tests/test_third_party_license_inventory.py \
  tests/test_render_release_gate_evidence.py tests/test_documentation_freshness.py \
  tests/test_public_open_source_docs.py tests/test_repository_publication_checklist.py
# 70 passed
```

## Node suite

```bash
cd desktop-electron && XFIN_PYTHON=$PWD/../.venv/bin/python npm test
```

- `# tests 519`, `# pass 519`, `# fail 0`, `# skipped 0`, `# todo 0`; exit code `0`.
- Baseline before this change was 515 with `XFIN_PYTHON`; the four additions are the W2
  renderer cases and the W8 integration test. Without `XFIN_PYTHON` the integration test
  reports `skipped` instead of failing, which keeps bare `npm test` green in environments
  with no interpreter configured.

## Desktop launch

```bash
cd desktop-electron && env -u ELECTRON_RUN_AS_NODE XFIN_PYTHON=$PWD/../.venv/bin/python npm start
```

Observed, in order:

1. `npm run build` (main + renderer `tsc`, asset copy) exited 0.
2. The app process stayed alive as the Electron main process
   (`node_modules/electron/dist/Electron.app/Contents/MacOS/Electron .`).
3. `lsappinfo` reports it as a **Foreground** GUI application
   (`com.github.Electron`, pid 82997, `type="Foreground"`), i.e. registered with the window
   server rather than running as a headless process.
4. Its Chromium profile under `~/Library/Application Support/XfinAudio Next/` was created and
   `chromium-session/blob_storage` written within the run.
5. It spawned the real Python core bridge as a child:
   `Python -m xfinaudio.headless --data-dir "/Users/freddymolina/Library/Application Support/XfinAudio Next"`.
6. No error output after the build.

Honest limits of this evidence: no screenshot was captured (`screencapture -x` produced no
file — the harness process has no screen-recording permission), and no desktop interaction was
automated, so the launch is proven by the process tree, the window-server registration and the
live bridge child, not by a visual assertion of rendered content.

Environment note with a real failure and its cause: the first launch attempt inherited
`ELECTRON_RUN_AS_NODE=1` from this session's environment, so the Electron binary executed the
main script as plain Node and died with
`TypeError: Cannot read properties of undefined (reading 'setName')` at
`.out/main/main.js:27`. That is a harness artifact, not a repository defect; unsetting the
variable for the child process makes the app start normally. It is recorded here because a
future automated launch that inherits the variable will see the same crash.

## Defects found and fixed during verification

| Found by | Defect | Fix |
|---|---|---|
| gate run 1 (tests) | `docs/third-party-license-inventory.md` named `PySide6` while two guards ban the token in that document | reworded the removal sentence to name the Qt desktop and the commit `4e31a3a`; the guards were left untouched rather than relaxed |
| gate run 2 (lint) | `E501` (190 > 120) in the new `tests/test_sdd_config_matches_project.py` | wrapped the comprehension |
| format step | `ruff format --check` would reformat `tests/test_documentation_freshness.py` and `tests/test_playlist_file_export.py` | formatted both; 315 files clean |
| evidence regeneration | `docs/release-candidate-evidence.md` still advertised `coverage` with `--cov-fail-under=70` and a removed PyInstaller check-only gate | regenerated from the report; the stale rows are gone and the remaining rows match the nine gates that exist |
| lock regeneration | the earlier claim that `uv pip compile --generate-hashes` cannot resolve here was an artifact of `UV_OFFLINE=1` in the environment, not a missing network; the committed `packaging/linux/requirements-build.txt` was stale against the snapshot (it omitted `setproctitle` and `watchdog`, kept a `cloudpickle` nothing pulls in, and pinned `packaging` 26.3 against the locked 25.0) | regenerated with `uv pip compile --generate-hashes --python-platform linux … -o packaging/linux/requirements-build.txt` (exit 0, 37 hash-locked pins); the `--python-platform linux` flag keeps the Darwin-only `macholib` pin in `packaging/macos/requirements-build.txt`, whose include structure was left unchanged |

## Freezer lock regeneration (was the open item)

`packaging/linux/requirements-build.txt` was regenerated in this session and the open item is
closed:

- `env -u UV_OFFLINE uv pip compile --generate-hashes --python-platform linux
  packaging/linux/requirements-build.in -o packaging/linux/requirements-build.txt` → exit 0,
  37 pins, every one hash-locked, header records exactly that command.
- The result follows `uv.lock` through the snapshot: `packaging==25.0`,
  `setproctitle==1.3.7` and `watchdog==6.0.0` present, no `cloudpickle`, no `macholib`.
  Some transitive pins are therefore *lower* than the stale Qt-era resolution they replace
  (`certifi` 2026.5.20 vs 2026.7.22, `numpy` 2.4.6 vs 2.5.3) — that is the point of
  following the lock instead of an independent resolve.
- `packaging/macos/requirements-build.txt` is unchanged: it still includes the Linux lock and
  adds hash-pinned `macholib==1.16.4`, which is one entry more than the Linux lock's 37.
- First attempt without `--python-platform linux` resolved for the Darwin host and added
  `macholib` to the Linux lock; it was rejected by inspection and replaced, and that is why
  the flag is now part of the documented command.
- New guards (strict TDD: RED before GREEN) in
  `tests/test_headless_requirements_lock_drift.py`, which grew from 5 to 8 tests:
  `test_compiled_freezer_lock_is_a_hash_locked_export`,
  `test_compiled_freezer_lock_agrees_with_the_headless_snapshot`, and
  `test_macos_freezer_lock_includes_the_linux_lock_and_only_adds_darwin`. RED for the
  agreement test was the real defect: restoring the committed lock from `HEAD` produced
  `AssertionError: requirements-build.txt omits headless pins: ['setproctitle', 'watchdog']`.
  RED for the export test was a temporary probe that stripped two `--hash` lines and produced
  `pins without a hash: ['altgraph']`. 8 passed afterwards.
- `docs/third-party-license-inventory.md` and `packaging/linux/README.md` were updated to
  describe the regenerated file and the command that reproduces it.

## Limitations

- No live AI provider call, credential, or real Mixed In Key library was exercised.
- Native macOS behavior beyond app launch (signing, notarization, DMG, clean-account run) was
  not observed.
- The regenerated freezer lock was verified structurally (hash-locked pins, agreement with
  the snapshot, autogenerated header) and by the guards above; no Linux freezer build was
  executed here, so the frozen bundle itself remains unverified on Linux.
- Items 9–11 of the review (62 parked changes, oversized modules, duplicated validation
  constants, `*-host.ts` lifecycle duplication, the dead
  `application/playlist_file_export.py` surface) were reported with evidence and deliberately
  not changed; they need their own change and their own RED.

## Post-gate additions

The green gate ran on the working tree before it was committed, so the question is whether the
commits carry exactly what the gate inspected. They do, and the check is reproducible: of the 55
path hashes recorded before committing (`git hash-object` per path, `/tmp/manifest-gated.txt`),
54 are byte-identical to the blobs now in `HEAD`. The single remaining path is
`odd/tasks/ai-playlist-improvement.md`, whose working-tree diff belongs to the earlier I5 cycle
rather than to this change and was therefore left uncommitted.

`verify-report.md` and `state.yaml` were written after the final gate run. Both live under
`openspec/`, which the documentation-freshness guard excludes, and the source package excludes;
they were revalidated with `ruff check .` and `ruff format --check .` (clean) and do not alter the
gate result for the source tree.

## Confirmation

The corrections are committed locally on `feat/ai-playlist-improvement` as nine work-unit commits
between `3172b4f` and the change-record commit that carries this file. No `git push`, tag, merge
or release was performed.
