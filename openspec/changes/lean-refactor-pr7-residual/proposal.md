## Why

After PRs 5 and 6, `main_window.py` is 1033 LOC — down from 1770 LOC at the start of
the chain (40% reduction). It is still well over the 400-line review budget. The
remaining bloat is in 4 places: signal wiring (cross-cutting but extractable per-screen),
build_layout + build_widgets (should be fully in `layout.py`), `_initialize_window_state`
(should be a factory function), and the 15 property accessors (should be direct
attributes on `AppState`).

This PR does all 4 extractions in one commit. The combined LOC reduction is large
enough to bring `main_window.py` close to the 400-line target.

## What changes

### 1. Per-screen signal wiring

`_connect_widget_signals` (70 LOC) is replaced by per-screen `connect_signals(window)`
methods. `MainWindow` iterates over the screens and calls each one. Each screen
owns its own signal-to-slot wiring.

### 2. Full `build_layout` + `build_widgets` move

The remaining body of `_build_layout` and `_build_widgets` (~110 LOC) is moved to
`src/xfinaudio/desktop/layout.py` as `build_main_window_layout(window)` and
`build_main_widgets(window)`. MainWindow's methods become one-line shims.

### 3. `_initialize_window_state` factory

The body of `_initialize_window_state` (~80 LOC) is moved to
`src/xfinaudio/desktop/window_factory.py` as `initialize_window_state(window, scan_service,
repository, settings, settings_repository)`. MainWindow's method becomes a one-line
shim.

### 4. Property accessors move to `AppState`

The 15 property accessors on `MainWindow` (workflow_service, current_scan_cancellation_token,
selected_folder, scanned_records, _records_by_path, last_recommendation,
last_playlist_explanation, last_quality_report, last_dj_readiness_report,
last_prep_copilot_plan, applied_prep_copilot_variant_name, serato_export_history,
excluded_paths, locked_paths, playlist_removed_paths) are removed. The state lives
directly on `AppState`. Call sites use `main_window._state.<name>`.

For backward compat with the 50+ call sites that use `main_window.<name>`, a
`MainWindow.__getattr__` / `__setattr__` shim is added that delegates to
`self._state.<name>`. This keeps the public API stable while saving 120 LOC of
property boilerplate.

## Non-goals

- Renaming any public attribute on `AppState`.
- Changing the 848-test suite's assertion behavior.
- Splitting `MainWindow` into a `MainWindowShell` + `App` (the class name stays).

## Impact

- Net: ~400-500 LOC moved out of `main_window.py`; new main_window: ~530-630 LOC.
- 1 new file (`window_factory.py`).
- 1 file extended (`layout.py`).
- 7 screens get a `connect_signals(window)` method.
- 50+ call sites get transparent backward-compat shims via `__getattr__`/`__setattr__`.
- Review budget: this PR exceeds 400-line cap on purpose (large refactor, same
  pattern as PR 5 and PR 6).
- Risk: medium. Strict TDD applies: the 848-test suite is the contract.

## Honest review of the original estimate

The original audit estimated `main_window.py` could go under 400 LOC. After
PRs 5 and 6, it's at 1033 LOC. The remaining ~630 LOC is split:
- Window setup + lifecycle: ~150 LOC (mostly irreducible)
- Property accessors: ~120 LOC (savable via __getattr__)
- Signal wiring: ~70 LOC (savable per-screen)
- build_layout + build_widgets: ~110 LOC (savable to layout.py)
- _initialize_window_state: ~80 LOC (savable to factory)
- AppController construction + remaining shims: ~100 LOC (irreducible)

After this PR, the irreducible core is ~300-400 LOC. If the savings are larger
than expected, we might hit <400. If not, the realistic target is <600.
