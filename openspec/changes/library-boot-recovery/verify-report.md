# Verification

## Outcome

A failed desktop library bootstrap now leaves a visible recovery panel with an explicit retry that reloads only
through `listLibrary()`. Idle work still runs, but it can no longer hide the failure, and success still hides the
operation status.

## Evidence

- RED: `npm --prefix desktop-electron run build` passed; `node --test desktop-electron/tests/renderer.library-boot.test.mjs`
  ran 3 tests, 0 passed, 3 failed (missing recovery markup, empty failure message, no second load on retry).
- GREEN: build passed; the same command ran 3 tests, 3 passed, 0 failed.
- Focused regression: `node --test desktop-electron/tests/renderer*.test.mjs desktop-electron/tests/library-host.test.mjs
  desktop-electron/tests/library-status.test.mjs desktop-electron/tests/errors.test.mjs` ran 205 tests, 205 passed,
  0 failed, 0 skipped.

## Requirements

- Bootstrap rejection: the test throws `core_stopped` on the first `listLibrary()` and asserts a visible panel, a
  non-empty reason, and an enabled retry.
- Visibility through idle work: after `settle()` drains the idle `getLibraryStatus`/preferences work, the panel and
  reason are still present.
- Safe retry: the test asserts a second `listLibrary()` call, a rendered `library-total` of 2, a hidden panel, a
  hidden operation status, and that no `rescanLibrary`/`chooseLibrary` call happened.
- Idempotent retry: two retry clicks while the first attempt is pending produce exactly one additional load.

## Limits

These are fake-DOM renderer tests; they prove API scheduling and modeled state, not native visibility, geometry, or
a real Electron launch. The empty-GUI cause in the owner's account remains unproven, and this change does not claim
the packaged artifact is fixed. The full repository gate (`uv run python scripts/release_gate_check.py --run`) is
parent-owned and has not been run in this work unit.

## Bounded first paint (ODD work unit 2)

### Outcome

The Library now paints at most 200 rows on first render while keeping the full 10k-scale match set searchable,
sortable and reachable through an explicit "Mostrar 200 pistas más" control. `library-visible-count` still reports
every match, a distinct note states how many of how many are shown, and the Prep selects are populated lazily without
truncating any track or losing a selection.

### Evidence

- RED: `npm --prefix desktop-electron run build` passed; `node --test desktop-electron/tests/renderer.offline-app.test.mjs
  desktop-electron/tests/renderer.prep.test.mjs` ran 27 tests, 25 passed, 2 failed (650 rows painted instead of 200;
  651 Prep options built at boot instead of none).
- GREEN: build passed with 0 type errors; the same command ran 27 tests, 27 passed, 0 failed.
- Regression: `node --test desktop-electron/tests/*.test.mjs` ran 434 tests, 423 passed, 0 failed, 11 skipped
  (the 11 skips are the pre-existing environment-gated integrations).

### Requirements

- Bounded first paint: the 650-track fixture renders exactly 200 rows, reports `650 pistas`, and shows a
  `200 de 650` note with an enabled load-more control.
- Full access: three show-more activations reach all 650 rows and then hide the affordance; a search matching 61 rows
  renders all 61, and a search matching all 650 resets to a 200-row window.
- Search/sort preserved: search changes reset the window while matching still uses the full library; the key column
  (Tonalidad) stays present in rendered rows.
- No Prep truncation: the 650-track fixture proves `prep-start` and `prep-required` hold every track after population
  and that a selected ID survives the deferred build.

### Limits

The 10,391-row production shape is represented by 650 synthetic tracks: the shared fake-DOM harness rebuilds its
`descendants` index on every lookup, so 10k makes the test pathological without proving more. These tests prove
scheduling, slicing and modeled state, not native scroll cost, real Electron first paint, or the owner's empty-GUI
cause. Independent verification of work unit 2 additionally passed `uv run python scripts/release_gate_check.py --run`
(4205 Python tests, 94.45% coverage against the 89% floor; pyright 0 errors/warnings; ruff and source gates clean).
The canonical Qt-free Electron wrapper, `XFIN_PYTHON=/tmp/electron-venv/bin/python python scripts/electron_ci_check.py
--evidence-dir /tmp/electron-test-evidence`, passed 434/434 tests with zero skips. Neither check launched the
owner's app or proves its real Library UI is fixed.
