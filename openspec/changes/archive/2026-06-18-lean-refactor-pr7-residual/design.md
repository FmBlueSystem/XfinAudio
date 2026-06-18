# Design: Slice main_window residual

## Approach

Four extractions in a single commit:
1. Per-screen signal wiring
2. Full `build_layout` + `build_widgets` move
3. `_initialize_window_state` factory
4. Property accessors via `__getattr__`/`__setattr__`

The first three are mechanical method moves. The fourth uses Python's dunder
attribute access to keep the public API stable while removing 120 LOC of property
boilerplate.

## Files affected

### New file (1)

| Path | LOC target | Source |
|------|------------|--------|
| `src/xfinaudio/desktop/window_factory.py` | ~120 | `_initialize_window_state` body |

### Modified files (10)

| Path | Change |
|------|--------|
| `src/xfinaudio/desktop/main_window.py` | -400 to -500 LOC, +30 LOC of shims |
| `src/xfinaudio/desktop/layout.py` | +110 LOC (full `build_layout` + `build_widgets`) |
| `src/xfinaudio/desktop/screens/library_screen.py` | +5 LOC (connect_signals method) |
| `src/xfinaudio/desktop/screens/build_screen.py` | +5 LOC |
| `src/xfinaudio/desktop/screens/review_screen.py` | +5 LOC |
| `src/xfinaudio/desktop/screens/export_screen.py` | +5 LOC |
| `src/xfinaudio/desktop/screens/metadata_screen.py` | +5 LOC |
| `src/xfinaudio/desktop/screens/live_assistant_screen.py` | +5 LOC (already has connect_signals) |
| `src/xfinaudio/desktop/screens/my_playlists_screen.py` | +5 LOC |
| `src/xfinaudio/desktop/screens/playlist_editor.py` | +5 LOC |
| `src/xfinaudio/desktop/app_state.py` | +30 LOC (the 15 attribute additions) |

## Property accessor removal via dunder methods

```python
# main_window.py
class MainWindow(QMainWindow):
    # The 15 property accessors are REMOVED.

    def __getattr__(self, name: str) -> object:
        # Delegate AppState attributes
        if name.startswith("_"):
            raise AttributeError(name)
        state = self.__dict__.get("_state")
        if state is not None and hasattr(state, name):
            return getattr(state, name)
        raise AttributeError(name)

    def __setattr__(self, name: str, value: object) -> None:
        # Delegate AppState attributes (only for the 15 known names)
        if name in _APP_STATE_ATTRIBUTES and "_state" in self.__dict__:
            setattr(self._state, name, value)
            return
        super().__setattr__(name, value)
```

The `_APP_STATE_ATTRIBUTES` is a frozenset of the 15 names. This keeps the
property semantics for the 15 names while letting all other attribute
access (e.g., `self.folder_label`, `self.workflow_tabs`) go through
`__setattr__` as normal.

This is a real Python pattern. The risk is that some Qt internals use
`__setattr__` in ways that interact poorly with our override. The
`__getattr__` is safer (only called when normal lookup fails).

## Step-by-step

1. Pre-flight: `git status` clean; 848 tests pass.
2. Add the 15 attributes to `AppState` (if not already there). Verify tests.
3. Add `__getattr__` and `__setattr__` to `MainWindow`. Verify tests.
4. Remove the 15 property accessors from `MainWindow`. Verify tests.
5. Add `connect_signals(window)` to each screen. Move the relevant signal
   connections from `_connect_widget_signals` into the per-screen method.
   Update `MainWindow.__init__` to call each `connect_signals`. Remove
   `_connect_widget_signals`. Verify tests.
6. Move the full bodies of `build_layout` and `build_widgets` into
   `layout.py`. MainWindow's methods become shims. Verify tests.
7. Move `_initialize_window_state` body to `window_factory.py`. MainWindow's
   method becomes a shim. Verify tests.
8. Run full verify: pytest, ruff, pyright, hygiene check.
9. `wc -l src/xfinaudio/desktop/main_window.py` is under 700.
10. Single work-unit commit.
11. Push, open PR.

## Risks

- **`__setattr__` shadowing Qt**: MainWindow is a QMainWindow; Qt uses
  `__setattr__` internally. The override MUST call `super().__setattr__` for
  everything except the 15 AppState names. The `_APP_STATE_ATTRIBUTES`
  frozenset MUST be limited to those 15.
- **`__getattr__` recursion**: the `__getattr__` MUST not recurse on
  `self._state` when `_state` is not yet set (e.g., during `__init__`).
  The check `if "_state" in self.__dict__` handles this.
- **Screen `connect_signals` methods may need access to MainWindow's
  private state**: pass `window` and let the screen call
  `window.choose_folder` (which is still a method on MainWindow) or
  `window._library_controller.choose_folder` (direct controller call).
  The latter is cleaner but requires the screen to know about the
  controller. The former is more decoupled.
- **Property removal in test suite**: any test that uses
  `inspect.signature(MainWindow.workflow_service)` or similar introspection
  will break. The 848-test count includes such introspection. The apply
  step MUST verify tests pass.

## Rollback

Single `git revert <commit-sha>` restores the previous state.
