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
