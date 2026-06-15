# Phase 5: Responsive Layout

## Intent

Make the desktop window adapt to its available width and give power users a
distraction-free Full Screen mode, while remembering the window size and
position between launches.

## Scope

- Detect window width on resize and adjust the workflow sidebar width
  (180px when wide, 120px when narrow).
- On narrow windows, collapse the sidebar to icon-only navigation labels.
- Add a Full Screen mode that hides the sidebar and the status bar/controls.
- Persist window size and position in settings and restore them on launch.

## Success criteria

1. A pure function maps window width to sidebar width: 180px wide, 120px narrow.
2. Resizing the window below the narrow breakpoint collapses the sidebar to
   icon-only labels; widening restores full labels.
3. `set_full_screen(True)` hides the sidebar panel and status controls;
   `set_full_screen(False)` restores them.
4. Window geometry (width, height, x, y) round-trips through `WindowSettings`
   and is restored on construction.
5. All tests pass and all verification commands pass.

## Deviation note

The proposal/spec/design/tasks artifacts for this change were authored during
the apply phase from the orchestrator's explicit requirements, because the
change directory was created empty (no upstream proposal/spec/design existed).
Acceptance criteria were taken verbatim from the orchestrator's required
implementation list.
