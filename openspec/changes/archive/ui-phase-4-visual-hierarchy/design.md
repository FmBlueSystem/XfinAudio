# Design: Visual Hierarchy

## Decision question

How do we express action priority and guide empty screens without restructuring layouts?

## Alternatives considered

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. objectName + theme QSS + size hints | Minimal churn; centralized styling; testable | Two emphasis tiers only | **Selected** |
| B. Custom QPushButton subclasses | Reusable | New classes, more surface, over-engineered for 2 tiers | Rejected |
| C. Inline per-widget stylesheets | Local | Duplicated; hard to keep consistent | Rejected |

## Approach

- `theme.py`: add `QPushButton#secondaryAction` (muted, smaller padding) and
  `QFrame#sectionDivider` rules; primary accent already exists on `#primaryAction`.
- Screens: assign `objectName` to primary/secondary buttons, set min/max height,
  insert a `QFrame.HLine` divider before each table, and add empty-state `QLabel`s.
- Empty-state visibility is driven from existing state (`selected_folder`,
  `scanned_records`, recommendation presence) inside each screen's `render`.

## Affected files

- `src/xfinaudio/desktop/theme.py`
- `src/xfinaudio/desktop/screens/library_screen.py`
- `src/xfinaudio/desktop/screens/build_screen.py`
- `src/xfinaudio/desktop/screens/export_screen.py`
- `tests/test_library_screen.py`
- `tests/test_build_screen.py`
- `tests/test_export_screen.py`
