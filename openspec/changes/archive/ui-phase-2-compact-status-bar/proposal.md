# Phase 2: Compact Status Bar

## Intent

Move status labels to a compact status bar at the bottom to reclaim ~60px of vertical space for the track table.

## Scope

- Create a `StatusBar` widget with 3 sections: folder, guidance, scan progress
- Move `folder_label`, `library_guidance_label`, `scan_progress_label` to status bar
- Add a toggle button to show/hide the status bar
- Default to hidden, show only during scan operations

## Success criteria

1. Status bar is at the bottom of the window
2. Status bar is hidden by default
3. Status bar shows during scan operations
4. All tests pass
5. All verification commands pass
