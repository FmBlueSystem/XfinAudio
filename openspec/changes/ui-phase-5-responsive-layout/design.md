# Design: Responsive Layout

## Decision question

How do we make the window responsive and Full-Screen-capable without
restructuring the existing `QHBoxLayout` sidebar/stack composition or breaking
the 99 pinned `test_main_window.py` assertions?

## Alternatives considered

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Pure width→width function + `resizeEvent` hook + `set_full_screen` toggle | Testable without a real WM; minimal churn; reuses existing panel widgets | Adds one event override | **Selected** |
| B. QSplitter with collapsible panes | Native collapse | Restructures layout; breaks pinned panel-contract tests | Rejected |
| C. Qt stylesheet media-query emulation | Declarative | PySide6 has no media queries; would need custom polling | Rejected |

## Approach

- `settings.py`: add a frozen `WindowSettings` pydantic model
  (`width`, `height`, `x`, `y`, all optional ints) and wire it into
  `AppSettings.window`. This satisfies geometry persistence (R4) and round-trips
  through the existing `SettingsRepository` JSON dump/validate.
- `library_screen.py` is unaffected structurally; responsiveness lives in
  `main_window.py`. (The orchestrator listed `library_screen.py` as an expected
  file, but the sidebar it targets is owned by `MainWindow`; no library-screen
  change is required and forcing one would add churn without behavior. Noted as
  a deviation.)
- `main_window.py`:
  - Module-level constants `_SIDEBAR_WIDTH_WIDE = 180`,
    `_SIDEBAR_WIDTH_NARROW = 120`, `_NARROW_BREAKPOINT = 900`.
  - Pure function `responsive_sidebar_width(width)` (R1) — no Qt, no side
    effects, trivially unit-tested.
  - Keep a reference to the `sidebar_panel` widget so resize/full-screen can
    mutate it. Replace `setFixedWidth(180)` with `_apply_sidebar_width()` driven
    by the responsive function.
  - `resizeEvent` override calls `_apply_responsive_layout(self.width())` (R2):
    sets panel width and toggles `ListView` icon-only mode via per-item text
    show/hide (store full labels, blank the visible text when narrow).
  - `set_full_screen(enabled)` (R3) hides/shows the sidebar panel and the status
    controls row, and toggles the Qt `showFullScreen`/`showNormal` window state.
  - Constructor restores geometry from `settings.window` when present, and
    `closeEvent` persists current geometry via `settings_repository`.

## Affected files

- `src/xfinaudio/config/settings.py`
- `src/xfinaudio/desktop/main_window.py`
- `tests/test_main_window.py`
- `tests/test_settings.py` (geometry round-trip)
