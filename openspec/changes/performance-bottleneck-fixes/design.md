# Design: Performance Bottleneck Fixes

## Technical Approach

Seven isolated, behavior-preserving fixes across the recommendation engine and PySide6
desktop. Each maps 1:1 to a proposal scope item. Two fixes deviate from the proposal's
suggested mechanism after reading the actual code (documented below as decisions).

## Architecture Decisions

| Decision | Choice | Rejected | Rationale |
|----------|--------|----------|-----------|
| Fix 1 cache | Session dict `_score_cache` threaded into `recommend_sequence`/`recommend_playlist`, cleared per `recommend_playlist` call | `functools.lru_cache` (proposal) | `score_transition` args include pydantic models + a `Collection[BoostRule]` that are not reliably hashable; a process-global LRU leaks across sessions and weights/config changes. Explicit dict keyed by identity is correct and clearable. |
| Fix 1 key | `(left.path, right.path, id(weights), id(config), id(boost_rules))` | path-only key | `weights`, `config`, `boost_rules` all alter the score and are immutable per recommend call, so identity is a safe, cheap discriminator. |
| Fix 3 order | Pre-filter candidate list before `recommend_sequence`; remove post-optimizer drop | keep post-drop | Optimizer must not spend TSP work on tracks that get dropped; pre-filter satisfies success criterion. |
| Fix 5 cap | `recommend_sequence(exact_limit: int = 20)` default → `15` | new constant | `exact_limit` is a named param (optimizer.py:29), not a magic number; lower the default only. |
| Fix 7 | Delete leftover root `build/`+`dist/`; add `conftest.py` autouse guard | edit `.gitignore` | `.gitignore` ALREADY lists `build/`+`dist/` (lines 26-27). Tests fail because the dirs physically exist at project root NOW. Proposal premise is already met; real fix is removal + guard. |

## Data Flow (Fix 1)

    recommend_playlist (clears _score_cache={})
         │ passes cache
         ▼
    recommend_sequence ──→ _score_matrix ──→ score_transition(…, cache=_score_cache)
                                                   │ hit → return cached
                                                   └ miss → compute, store

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `recommendation/scoring.py` | Modify | Add optional `cache: dict | None = None` param to `score_transition`; check/populate before compute. |
| `recommendation/optimizer.py` | Modify | Thread `cache` through `recommend_sequence`/`_score_matrix`; change `exact_limit` default `20`→`15`. |
| `recommendation/playlist_service.py` | Modify | Create `_score_cache={}`; pre-filter BPM jumps before sequencing; remove post-drop; pass cache to scoring helpers. |
| `desktop/main_window.py` | Modify | Add search `QTimer` debounce; `_current_tab_index` + lazy `_render_screens`; `closeEvent` uses controller `cancel()`. |
| `desktop/scan_controller.py` | Modify | Running-thread guard + `_current_request_id`; public `cancel()` that interrupts thread. |
| `desktop/recommendation_controller.py` | Modify | Same guard/request-id/`cancel()` pattern. |
| `tests/conftest.py` | Modify | Autouse session guard removing root `build/`/`dist/`. |
| root `build/`, `dist/` | Delete | Leftover PyInstaller artifacts causing hygiene test failures. |

## Interfaces / Patterns

**Fix 1** — `scoring.py`:
```python
def score_transition(left, right, weights=DEFAULT_WEIGHTS, boost_rules=None,
                     config=None, cache=None) -> TransitionScore:
    key = (left.path, right.path, id(weights), id(config), id(boost_rules)) if cache is not None else None
    if cache is not None and key in cache:
        return cache[key]
    ...  # existing body builds `result`
    if cache is not None:
        cache[key] = result
    return result
```
`recommend_playlist`: `score_cache: dict = {}` at top; pass into `recommend_sequence(..., cache=score_cache)` and `_score_ordered_tracks(..., cache=score_cache)`.

**Fix 2** — `main_window._initialize_window_state`: `self._search_debounce = QTimer(self); self._search_debounce.setSingleShot(True); self._search_debounce.setInterval(150)`. In `_connect_widget_signals` replace direct `textChanged` filter connect with `textChanged.connect(self._search_debounce.start)` and `self._search_debounce.timeout.connect(lambda: self._apply_song_filter(clear_selection=True))`.

**Fix 3** — `recommend_playlist`: run `remaining_tracks, _ = _drop_generated_tracks_after_impossible_bpm_jumps(remaining_tracks)` BEFORE the `recommend_sequence` branch; delete the post-`ordered_tracks` drop block (lines 104-110).

**Fix 4** — `_build_layout` after tab adds: `self.workflow_tabs.currentChanged.connect(self._on_tab_changed)`; track `self._current_tab_index`. `_render_screens` calls `.render()` only on the screen at `_current_tab_index` (keep `_update_tab_states`). `_on_tab_changed(index)`: set index, render that screen with current `_state`.

**Fix 6** — both controllers:
```python
def start_X(self, ...):
    if self._thread and self._thread.isRunning():
        self._thread.requestInterruption(); self._thread.wait(500)
    self._current_request_id += 1
    rid = self._current_request_id
    # worker captures rid; on finish compare and ignore if rid != self._current_request_id
def cancel(self):
    if self._thread and self._thread.isRunning():
        self._thread.requestInterruption(); self._thread.wait(500)
```
`closeEvent`: `self._scan_controller.cancel(); self._recommendation_controller.cancel()` instead of poking `_scan_thread.quit()`.

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | Cache hit returns identical `TransitionScore`; cleared per call | scoring/playlist_service tests |
| Unit | `exact_limit=15` boundary: n=15 exact, n=16 heuristic | optimizer test |
| Unit | BPM pre-filter removes jumps before optimizer; optimizer never sees them | playlist_service test |
| Integration | Debounce: rapid `textChanged` runs filter once after 150ms | qtbot timer test |
| Integration | Lazy render: only active screen `.render()` called; tab switch renders new screen | spy/mock screens |
| Integration | Second `start_*` interrupts first; stale request ignored | controller tests |
| Regression | `build/`/`dist/` absent during run | existing packaging/release-gate tests pass |

## Migration / Rollout

No migration. Each fix is one file (or paired controller). `git revert` per commit restores prior behavior.

## Open Questions

- [ ] Fix 6: does `BackgroundWorker`/`ScanWorker` expose a cooperative interruption check, or does `requestInterruption()` only mark the flag (work still completes, result ignored via `_current_request_id`)? Confirm during apply; the request-id stale-guard makes correctness independent of cooperative checks.
- [ ] Fix 7: should the conftest guard also remove `release-dist/` / `.release-evidence/`? Current failing tests only assert `build/`+`dist/`; keep guard scoped to those unless tests say otherwise.
