# Design: Replace Tab Sidebar with Proper Navigation

## Decision question

How do we fix the sidebar overlap without breaking the existing 7-screen navigation?

## Alternatives considered (Arbor-style)

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Replace QTabWidget with QListWidget + QStackedWidget | Full layout control; no Qt rendering bug; clean styling. | Touches main_window layout. | **Selected.** |
| B. Add setDocumentMode(True) to QTabWidget | Minimal change. | May not fix the overlap. | Rejected. |
| C. Move tabs to North | Avoids the bug. | Big UX change. | Rejected. |

## Architecture impact

- `MainWindow._build_layout` builds a `QHBoxLayout` with a `QListWidget` sidebar (fixed width) + `QStackedWidget` content.
- `QListWidget.currentRowChanged` is connected to `QStackedWidget.setCurrentIndex`.
- The 7 screens are added to the stacked widget instead of the tab widget.
- The existing `workflow_tabs.setCurrentIndex(n)` calls in coordinators are updated to `workflow_stack.setCurrentIndex(n)` (or we keep the name `workflow_tabs` as an alias for the stacked widget to minimize changes).

## Affected files

- `src/xfinaudio/desktop/main_window.py`
- `src/xfinaudio/desktop/theme.py` (sidebar styles)
- Tests: `tests/test_main_window.py`, `tests/test_navigation_controller.py`

## Safety

- No audio mutation.
- No DSP scope expansion.
- No live Serato Database V2 writes.
