# Tasks: Performance Bottleneck Fixes

> Change: `performance-bottleneck-fixes`
> Artifact mode: `hybrid`
> Verification command: `uv run pytest tests/ -x`

---

## Task 1 — Add session-scoped transition score cache [x]

**Files to modify:**
- `src/xfinaudio/recommendation/scoring.py`
- `src/xfinaudio/recommendation/optimizer.py`
- `src/xfinaudio/recommendation/playlist_service.py`

**What to change:**

1. **`scoring.py`** — Add optional `cache: dict | None = None` parameter to `score_transition()`:
   - Before computation: build key `(left.path, right.path, id(weights), id(config), id(boost_rules))` if `cache is not None`.
   - If key is in cache, return `cache[key]` immediately.
   - After building result: if `cache is not None`, store `cache[key] = result`.
   - Existing callers (no cache arg) continue to work unchanged.

2. **`optimizer.py`** — Thread `cache` through `recommend_sequence()` → `_score_matrix()`:
   - `recommend_sequence` accepts optional `cache: dict | None = None` and passes it to `_score_matrix`.
   - `_score_matrix` passes `cache` to each `score_transition` call.

3. **`playlist_service.py`** — Create and manage the cache:
   - At top of `recommend_playlist()`, create `_score_cache: dict[tuple, TransitionScore] = {}`.
   - Pass `cache=_score_cache` to `recommend_sequence()`.
   - Pass `cache=_score_cache` to `_score_ordered_tracks()` → `score_transition()`.

**Verification:**
```
uv run pytest tests/test_transition_scoring.py tests/test_sequence_optimizer.py tests/test_playlist_service.py -x
```

---

## Task 2 — Debounce search filter with QTimer

**Files to modify:**
- `src/xfinaudio/desktop/main_window.py`

**What to change:**

1. **Add `QTimer` import** — Already imported from `PySide6.QtCore` (line 11), where `QTimer` is available alongside `QCoreApplication`, `Qt`, `Slot`.

2. **`_initialize_window_state`** (line 290) — Add after other state inits:
   ```python
   self._search_debounce = QTimer(self)
   self._search_debounce.setSingleShot(True)
   self._search_debounce.setInterval(150)
   ```

3. **`_connect_widget_signals`** (line 632) — Replace existing `textChanged` direct connect (line 636):
   - Change `self.song_search_input.textChanged.connect(lambda text: self._apply_song_filter(text, clear_selection=True))`
   - To: `self.song_search_input.textChanged.connect(self._search_debounce.start)`
   - Add: `self._search_debounce.timeout.connect(lambda: self._apply_song_filter(clear_selection=True))`
   - Read `self.song_search_input.text()` inside `_apply_song_filter` when `query is None` (already does: line 877).

**Verification:**
```
uv run pytest tests/test_main_window.py -x
```

---

## Task 3 — Move BPM pre-filter before optimizer

**Files to modify:**
- `src/xfinaudio/recommendation/playlist_service.py`

**What to change:**

1. **Move** the BPM-jump filter call from after `recommend_sequence()` to before it:
   - In `recommend_playlist()`, apply `_drop_generated_tracks_after_impossible_bpm_jumps()` to `remaining_tracks` (instead of the current `ordered_tracks`).
   - The call site is right before lines 94-101 (where `recommend_sequence` or `_apply_terminal_constraints` is invoked), after `remaining_tracks` is built on line 82.
   - Track `dropped_bpm_jump_count` as before.

2. **Delete** the post-optimizer drop block:
   - Remove lines 104-110 (the `ordered_tracks, dropped_bpm_jump_count = ...` line and the subsequent if-block that appends to `warnings`).
   - The warnings append logic moves up with the pre-filter call.

3. **Adjust `warnings` append** to use the pre-filter's `dropped_bpm_jump_count`.

**Verification:**
```
uv run pytest tests/test_playlist_service.py -x
```

---

## Task 4 — Lazy-render only visible tab screen [x]

**Files to modify:**
- `src/xfinaudio/desktop/main_window.py`

**What to change:**

1. **Add `_current_tab_index` tracking** — Add `self._current_tab_index: int = 0` in `_initialize_window_state` (around line 310).

2. **Connect `currentChanged` signal** — In `_build_layout` (line 189), after adding all tabs to `self.workflow_tabs`:
   ```python
   self.workflow_tabs.currentChanged.connect(self._on_tab_changed)
   ```

3. **Modify `_render_screens`** (line 345) — Instead of rendering all screens, only render the screen at `self._current_tab_index`. Keep `_update_tab_states()` call.

4. **Add `_on_tab_changed` handler**:
   ```python
   def _on_tab_changed(self, index: int) -> None:
       self._current_tab_index = index
       self._sync_state()
   ```
   `_sync_state` already calls `_render_screens`, which now only renders the active tab. But we need the tab-change to trigger full render of the newly visible screen immediately. Since `_render_screens` already reads `self._current_tab_index` (set in `_on_tab_changed`), calling `_sync_state` from `_on_tab_changed` handles this.

**Verification:**
```
uv run pytest tests/test_main_window.py tests/test_screens.py -x
```

---

## Task 5 — Lower exact optimizer cap to n=15 [x]

**Files to modify:**
- `src/xfinaudio/recommendation/optimizer.py`

**What to change:**

1. **Line 29** — Change default parameter:
   ```python
   exact_limit: int = 20,
   ```
   → `exact_limit: int = 15`

   This is the sole change. The TSP exact solver runs for `len(ordered) <= exact_limit` (line 40), so with `exact_limit=15` pools of 15 use exact, pools of 16+ use heuristic.

**Verification:**
```
uv run pytest tests/test_sequence_optimizer.py -x
```

---

## Task 6 — Add thread lifecycle guards to both controllers

**Files to modify:**
- `src/xfinaudio/desktop/scan_controller.py`
- `src/xfinaudio/desktop/recommendation_controller.py`
- `src/xfinaudio/desktop/main_window.py`

**What to change:**

### `scan_controller.py`

1. **Add `_current_request_id: int = 0`** in `__init__`.

2. **Add cancellation at start** — At top of `_start_scan_worker()`:
   ```python
   if self._scan_thread is not None and self._scan_thread.isRunning():
       self._scan_thread.requestInterruption()
       self._scan_thread.wait(500)
   self._current_request_id += 1
   rid = self._current_request_id
   ```

3. **Workers capture `rid`** — Pass `rid` to worker (e.g., via closure or attribute). On worker finish, compare `rid` vs `self._current_request_id` — discard if stale.

   Since the thread+worker are recreated each call, the simplest approach:
   - Store `rid` on the ScanWorker before moving to thread.
   - In `_on_worker_finished` callback, check if `self._scan_thread` is the same thread (avoids race with subsequent calls). But the simplest is: store `_current_request_id` before starting, and in the completion handler check `if rid != self._current_request_id: return`.

   Better: wrap the `_on_worker_finished` and `_on_worker_failed` connections with a lambda that captures `rid` and checks it against current.

4. **Add public `cancel()` method** — Interrupt and wait for the running thread:
   ```python
   def cancel(self) -> None:
       if self._scan_thread is not None and self._scan_thread.isRunning():
           self._scan_thread.requestInterruption()
           self._scan_thread.wait(500)
   ```

### `recommendation_controller.py`

Same pattern:
1. Add `_current_request_id: int = 0` in `__init__`.
2. At top of `start_recommendation()`, add cancel+wait for previous thread, increment id, capture rid.
3. Wrap handers with stale-request check.
4. Add public `cancel()` method.

### `main_window.py`

1. **`closeEvent`** (line 178) — Replace direct access to private thread attributes:
   ```python
   def closeEvent(self, event: object) -> None:
       self._audio_player.stop()
       self._scan_controller.cancel()
       self._recommendation_controller.cancel()
       super().closeEvent(event)
   ```

**Verification:**
```
uv run pytest tests/test_main_window.py -x
```

---

## Task 7 — Fix failing packaging/release-gate tests

**Files to modify:**
- Delete `build/` and `dist/` from project root
- `tests/conftest.py`

**What to change:**

1. **Delete `build/` and `dist/`** directories from `/Users/freddymolina/Documents/audio/` using `rm -rf`.

2. **Add autouse conftest guard** — In `tests/conftest.py`, add a session-scoped autouse fixture that asserts both `build/` and `dist/` are absent at test startup:
   ```python
   @pytest.fixture(autouse=True, scope="session")
   def _no_root_build_artifacts():
       """Prevent accidental test runs from a dirty checkout with build/ or dist/ present."""
       from pathlib import Path
       root = Path(__file__).resolve().parent.parent
       assert not (root / "build").exists(), f"Remove {root / 'build'} before running tests"
       assert not (root / "dist").exists(), f"Remove {root / 'dist'} before running tests"
   ```

**Verification:**
```
uv run pytest tests/test_pyinstaller_packaging.py tests/test_release_gate_check.py -x
```
