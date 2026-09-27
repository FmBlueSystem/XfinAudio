# Feature: Copilot variant selection survives Build screen re-renders

## Problem
On the Build screen, selecting a row in the Prep Copilot variants table does not stick:
any `_sync_state()` while Build is the visible tab re-renders with `lightweight=False`,
which runs `_populate_copilot_table()` (`setRowCount(0)` + fresh items) and destroys the
selection — even when the rendered rows are unchanged. `Apply Selected Variant` then
silently returns (`_on_apply_variant` bails on empty `selectedItems()`).

Verified offscreen: `selectRow(1)` → `render(same state)` → `selectedItems()==0`,
`currentRow()==-1`.

Sync sources that fire while the user is on Build: per-track spectral/danceability/loudness
completion callbacks (throttled to ≤200 ms), library watch service, spectral cohesion
slider, scan progress, metadata filters.

## Tasks
- [x] T1 — Render idempotence: cache the rendered row signature in `BuildScreen.render`;
      skip `_populate_copilot_table` when rows are unchanged so selection/currentRow survive.
- [x] T2 — Restore selection when rows do change (same-index restore when the count is
      unchanged; otherwise clear intentionally).
- [x] T3 — Replace the silent return in `_on_apply_variant` with a visible status message
      via the new `apply_without_selection_requested` signal wired to the window status label.
- [x] T4 — Offscreen tests: selection survives same-rows render; table updates when rows
      change; apply-without-selection reports status; controller-clear staleness regression
      (added during remediation, see below).
- [x] T5 — Work-unit commit on a feature branch with tests; commit identity below.

## Evidence
- Commit: `439809c` on branch `fix/copilot-selection-wipe` (fix(desktop): preserve copilot
  variant selection across build re-renders).

## Verification trail
- Writer RED→GREEN observed (3 of 4 new tests failed pre-fix as expected).
- Independent verifier confirmed the fix and the repro, and found one major interaction
  defect: the controller's controls-None branch cleared the table directly, leaving the
  new signature cache stale (empty table + full state on regenerate). Remediated with
  `BuildScreen.invalidate_copilot_cache()` + call in `prep_copilot.py`; verifier re-ran
  the runtime repro: PASS, defect closed.
- Final gate: pytest 27 passed (targeted) / 84 passed (-k subset); ruff check + format
  clean; pyright 0 errors on all touched files.

## Checks
- [x] `.venv/bin/python -m pytest tests/test_build_screen.py` (plus new tests) green.
- [x] Offscreen repro now shows selection surviving a same-rows render.
