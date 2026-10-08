# Apply progress

As-built record for the review remediation. Every unit below was built on the working
tree of `feat/ai-playlist-improvement` and landed there as local work-unit commits
(`70d6c0a` W1, `bb29fac` W2, `8d18125` W3, `ad593f4` W5, `3416410` W7, `7e0b2e3` W4,
`296cf09` W6, `95564bd` W8, plus the change-record commit for W9/W10); nothing was
pushed, tagged or merged. The delivery order was chosen so that each commit is green on
its own: the documentation-freshness guard (W4) needs the regenerated gate evidence and
the Qt-era cleanup (W7) already in place, and the SDD reconciliation (W6) needs the
`pyproject.toml` that W7 leaves behind.

## W1 — Export containment (`src/xfinaudio/exporting/playlist_file_export.py`)

- RED: the new cases in `tests/test_playlist_file_export.py` failed against the tree that
  passed a caller-supplied name straight to `write_text`.
- GREEN: `safe_target_name(value: str) -> str` keeps the final component and raises
  `ValueError("Playlist export name must be a single file name.")` when nothing usable
  remains; the plan resolves `chosen_name = requested_name or variant_name or
  default_export_filename(...)` against the export folder and raises
  `ValueError("Playlist export name must resolve inside the export folder.")` otherwise.
- Focused result: `tests/test_playlist_file_export.py` 15 passed.

## W2 — Renderer request immutability (`desktop-electron/renderer/`)

- RED: the new renderer cases failed because `setRequest` called `reset()` while a paid
  `ask` was pending, dropping the authorized binding.
- GREEN: `setRequest` returns early when `this.pending === 'ask'`, when the surface is not
  editable, when the value is not a string, or when the value is already staged; only a
  genuine change resets the controller and stages the new text.
- View: `canAct()` / `heldByLocalJob()` / `localEditable()` distinguish a local job from a
  paid call, and the panel shows the local-hold notice while the field is not editable.
- Focused result: `optional-ai.test.mjs` 34 passed, `optional-ai-view.test.mjs` 17 passed,
  `npm run build` exit 0.

## W3 — Headless lock drift

- `desktop-electron/requirements-headless.txt` regenerated from `uv.lock` with
  `UV_OFFLINE=1 uv export --frozen --no-dev --no-emit-project`: 601 lines, 33 hash-locked
  pins. `desktop-electron/requirements-headless.in` deleted.
- `packaging/{linux,macos}/requirements-build.in` now consume the snapshot and add the
  freezer pins (`pyinstaller==6.20.0`, `pyinstaller-hooks-contrib==2026.5`,
  `altgraph==0.17.5`, `packaging==25.0`, `setuptools==82.0.1`, plus `macholib==1.16.4` for
  macOS).
- `tests/test_headless_requirements_lock_drift.py` (8 tests) compares the snapshot with
  `uv.lock` as text, so a future `uv lock` without a snapshot refresh fails the suite, and
  the last three of those tests guard the compiled freezer lock the same way.
- `docs/third-party-license-inventory.md` now carries the 33-row hash-locked table and the
  export mechanism; `packaging/macos/README.md` states that the freezer lock is the only
  supported input and that Electron comes from the npm lock.
- The freezer lock was regenerated inside this change. An earlier note here claimed
  `uv pip compile --generate-hashes` cannot resolve in this session; that was wrong. The
  compile had only ever been attempted with `UV_OFFLINE=1` set in the environment, which is
  what refused the index, not the network. With that variable unset from the process
  environment, `uv pip compile --generate-hashes --python-platform linux
  packaging/linux/requirements-build.in -o packaging/linux/requirements-build.txt` exits 0
  and produces 37 hash-locked pins. The commit corrects the record instead of keeping the
  stale conclusion.

## W4 — Documentation freshness

- New `tests/test_documentation_freshness.py` (11 tests): tracked document set from
  `git ls-files`, referenced-path existence, `uv run` target resolution, AI settings label
  agreement, historical-banner and registry rules, plus negative monkeypatched cases that
  prove the guard bites.
- New `docs/architecture/README.md` registry; superseded architecture notes carry a
  historical banner naming `4e31a3a`.
- Fixed in place: `docs/open-source-release-backlog.md`,
  `docs/safe-export-folder-settings.md`, `docs/scan-progress-cancel.md`,
  `docs/ui-empty-states-warning-clarity.md`, `docs/harmonic-mixing.md`,
  `docs/restart-handoff-2026-09-24.md`, `docs/release-readiness-smoke.md`,
  `docs/packaging-strategy.md`, `docs/pyinstaller-packaging-spike.md`,
  `tests/fixtures/mik_processed/README.md` and the matching doc test.
- `openspec/config.yaml` reconciled with `pyproject.toml` and `uv.lock` (PySide6 and
  pyobjc removed, `packaging`/`pyloudnorm` added, floor `>=3.12`, UI layer no longer
  "pytest + PySide6 offscreen"), guarded by `tests/test_sdd_config_matches_project.py`
  (9 tests including two negative cases).

## W5 — Observability of discarded failures

- `library/track_repository.py`: module `LOGGER` and
  `_log_unreadable_profile(label, *, path, exc)` warn once per unreadable profile; the six
  `_deserialize_*_profile` helpers take `path` so the warning names the file.
- `library/scan_service.py`: an unreadable audio MD5 signature warns and keeps the
  size/mtime freshness fallback.
- `tests/test_swallowed_exception_observability.py` (8 tests) covers both sites and asserts
  the analyzer `None` contract in `audio/*.py` is untouched.

## W6 — SDD state and skill

- `openspec/changes/ai-playlist-improvement/state.yaml`: `status: verify`, `verify:
  complete`, `next_recommended: native-validation`, with notes recording that an agent
  reconciled provider-owned phase fields during a review and claims no approval.
- `.atl/skills/gentle-ai-sdd-tdd/SKILL.md`: the verification section now runs
  `uv run python scripts/release_gate_check.py --run` first and states that the coverage
  floor lives in `pyproject.toml` and that `--cov-fail-under` must never be passed.
- Guard: `tests/test_release_gate_check.py` asserts the skill names the gate command, points
  at `pyproject.toml` for the floor and contains no `--cov-fail-under` value; the file's
  other coverage-floor guards keep passing.

## W7 — Qt residue

- Deleted the Qt Linguist catalogs (`translations/xfinaudio_{en,es}.ts`,
  `assets/translations/xfinaudio_{en,es}.qm`), their empty directories, the
  `assets/translations` wheel force-include and the dead
  `extend-per-file-ignores` entry for the removed translation script, all guarded by
  `tests/test_documentation_freshness.py`.
- Removed `QT_QPA_PLATFORM: offscreen` from `.github/workflows/non-audio-release-gates.yml`
  and `.github/workflows/publish-to-pypi.yml`, guarded by
  `tests/test_publish_workflow_gates.py` (21 passed).
- Deleted the untracked `src/xfinaudio/desktop/` bytecode tree (91 `.pyc`, no tracked file).
- Reduced `src/xfinaudio/ai/connection_test.py` from the retired Qt-dialog state machine to
  the single `PROBE_MESSAGE` constant after proving RED in
  `tests/test_ai_connection_test.py` (1 failed, 2 passed before the change; 3 passed after,
  together with the headless AI suites: 132 passed).
- Rewrote `docs/ai-settings.md` with the shipped Electron labels (`Ajustes de IA`,
  `Elegir archivo de credenciales…`, `Quitar fuente de credenciales`, `Guardar ajustes de
  IA`, `Probar conexión`, `Cancelar`), keeping the English section and the pinned security
  fragments; the new label guard failed first, then passed.

## W8 — Real-core improvement integration

- Delegated to a subagent against a fixed contract, and independently verified here.
- New `desktop-electron/tests/editor-improvement.integration.test.mjs` drives the real
  `PythonBridge` and the real headless core: scan → generate → save → open → AI settings →
  prepare → run → apply, asserting the core-computed UUID and 64-hex digest, the exact
  reversed order, the absence of any draft id or library path from the outbound provider
  body, three real-core rejections (`invalid_edit` twice, `stale_edit`) that persist
  nothing, and a bridge restart that reads the improved order back from disk.
- Honest RED result: no functional RED exists — the behavior was already correct and only
  the renderer test double hid it. Non-vacuity was proved instead with a temporary probe in
  the new file (provider echoed the draft order), which failed the reversal assertion, and
  was then reverted.
- Focused result: 1 passed / 0 failed with `XFIN_PYTHON`; 1 skipped without it, so the plain
  `npm test` path stays green.

## W9 — Durable record

These artifacts. Documentation only: no source or test change in W9 itself; it records the
units above and is landed in the last commit together with the W10 evidence.

## W10 — Verification

- Gate of record: exit 0, `overall_status: passed`, nine gates passing, 2822 passed,
  91.83% coverage against the 89 floor configured in `pyproject.toml` (no
  `--cov-fail-under` on any command line). Details in `verify-report.md`. Five runs happened
  in the phase: two failed on the defects below, two passed at 2819, and the final one was
  re-run at 2822 after the freezer lock was regenerated, because a tracked lock change
  invalidates the earlier result.
- Two earlier runs of the same gate found two defects that were then fixed: a banned
  `PySide6` mention in `docs/third-party-license-inventory.md` (reworded, guards
  untouched) and a 190-character line in `tests/test_sdd_config_matches_project.py`.
  `ruff format` also asked for two of the new test files to be reformatted.
- Node suite with `XFIN_PYTHON`: 519 tests, 519 passed, 0 failed, 0 skipped (baseline 515).
- `docs/release-candidate-evidence.md` regenerated from the green report; the stale
  `--cov-fail-under=70` and PyInstaller check-only rows are gone.
- Electron app launched against this tree and confirmed by process evidence; the
  `ELECTRON_RUN_AS_NODE=1` artifact of the first attempt is recorded in
  `verify-report.md`.
- No task stays unchecked: the freezer `packaging/linux/requirements-build.txt` lock was
  regenerated and is now guarded by three additional drift tests (see W3 above).
- The work was then landed as local work-unit commits on `feat/ai-playlist-improvement`
  (W1 → W2 → W3 → W5 → W7 → W4 → W6 → W8 → W9+W10, the order the header explains), one per unit,
  each carrying the test that proves it, with the unit's focused tests re-run after its commit.
  No push, no tag, no merge: `origin/main` is untouched and the commits remain local. The
  Electron app left running from the launch check was closed afterwards.
