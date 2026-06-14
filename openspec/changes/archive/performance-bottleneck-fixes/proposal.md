# Proposal: Performance Bottleneck Fixes

## Intent

Fix seven performance and quality bottlenecks identified across the xfinaudio recommendation engine and desktop UI. These issues cause excessive CPU usage, UI stutter on large libraries, wasted TSP optimization work, redundant screen renders, and race conditions in background threads.

## Scope

### In Scope
1. Memoize `score_transition` in `scoring.py` to eliminate ~50% of scoring CPU.
2. Debounce search filter in `main_window.py` with a 150ms `QTimer` delay.
3. Pre-filter BPM-jump candidates in `playlist_service.py` **before** the TSP optimizer.
4. Lazy-render only the visible tab in `main_window.py`; skip rendering hidden screens.
5. Lower exact optimizer cap from n=20 to n=15 in `optimizer.py`.
6. Add running-thread guards in `scan_controller.py` and `recommendation_controller.py`.
7. Fix two failing packaging/release tests by ensuring `build/` and `dist/` are absent during test execution.

### Out of Scope
- New product features or UI redesign.
- Changes to heuristic optimizer internals.
- Refactoring of controller architecture beyond the race-condition guard.

## Capabilities

### New Capabilities
None

### Modified Capabilities
- `desktop-main-window`: lazy tab rendering and debounced search filter change the update timing contract; observable behavior must remain equivalent.
- `dj-recommendation-safety`: BPM pre-filter and exact-to-heuristic threshold shift (n=20 → n=15) alter the recommendation computation path for 16–20 track pools.

## Approach

Apply targeted, behavior-preserving fixes:
- Use `functools.lru_cache` keyed by `(left.path, right.path, weights_hash)` for transition scoring.
- Add `QTimer.singleShot(150)` in the search filter handler; restart the timer on each keystroke.
- Move the existing BPM-jump exclusion logic from post-optimization to pre-optimization in `playlist_service.py`.
- Track the active tab in `main_window.py` and call `.render()` only for the visible screen; defer others until tab switch.
- Change the `exact_limit` constant in `optimizer.py` from `20` to `15`.
- Check `thread.isRunning()` at the top of `start_scan()` and `start_recommendation()`; ignore or cancel-and-restart if already active.
- Add a pytest fixture or `conftest.py` cleanup step that removes `build/` and `dist/` before the packaging tests run, or skip when present.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/xfinaudio/recommendation/scoring.py` | Modified | Add `lru_cache` to `score_transition`. |
| `src/xfinaudio/desktop/main_window.py` | Modified | Debounce search; lazy-render active tab only. |
| `src/xfinaudio/recommendation/playlist_service.py` | Modified | Move BPM-jump filter before TSP call. |
| `src/xfinaudio/recommendation/optimizer.py` | Modified | Lower exact solver cap to n=15. |
| `src/xfinaudio/desktop/scan_controller.py` | Modified | Guard against concurrent scan threads. |
| `src/xfinaudio/desktop/recommendation_controller.py` | Modified | Guard against concurrent recommendation threads. |
| `tests/test_pyinstaller_packaging.py` | Modified | Clean or skip when `build/`/`dist/` exist. |
| `tests/test_release_gate_check.py` | Modified | Clean or skip when `build/`/`dist/` exist. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Lazy render breaks tab-switch state sync | Low | Add explicit `.render()` call on tab-change signal. |
| Debounce hides real-time feedback | Low | 150ms is below human perception threshold for typing. |
| Heuristic results differ from exact for n=16..20 | Med | Characterize output variance with existing test data; accept if within tolerance. |
| Race-condition guard aborts legitimate re-runs | Low | Use cancel-and-restart, not ignore, for explicit user retries. |

## Rollback Plan

Revert the individual commits or roll back the branch. Each fix is isolated to a single file or pair of files with no schema or data migrations, so `git revert` of the relevant commit(s) restores prior behavior immediately.

## Dependencies

None

## Success Criteria

- [ ] `score_transition` cache hit rate >90% in repeated recommendation cycles.
- [ ] Search typing on a 10k-track library does not block the UI thread.
- [ ] TSP optimizer never receives candidates that will be dropped by BPM-jump filter.
- [ ] `_sync_state` render time is proportional to visible tabs, not total tabs.
- [ ] Exact optimizer runs only for n≤15; n=16..25 uses heuristic.
- [ ] Starting a second scan or recommendation cancels or ignores the first; no concurrent threads.
- [ ] `uv run pytest -q` passes with zero failures, including packaging and release-gate tests.
