# Phase 10: Undo/Redo

## Intent

Add undo/redo for destructive actions so users can recover from mistakes.

## Scope

- Add undo/redo stack for: remove track, reorder playlist, clear filters
- Add `Ctrl+Z` / `Ctrl+Shift+Z` shortcuts
- Add undo/redo buttons to the toolbar
- Show undo history in a dropdown

## Success criteria

1. Undo/redo works for remove track, reorder playlist, clear filters
2. Ctrl+Z triggers undo, Ctrl+Shift+Z triggers redo
3. Undo/redo buttons are in the toolbar
4. Undo history is shown in a dropdown
5. All tests pass
6. All verification commands pass
