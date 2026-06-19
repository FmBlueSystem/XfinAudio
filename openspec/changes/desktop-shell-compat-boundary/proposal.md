# Proposal: Desktop shell compatibility boundary

## Intent

Start Slice 5 from the layered architecture map by making MainWindow legacy layout method grafting explicit and isolated.

## Problem

`desktop/layout.py` currently both builds UI layout structures and installs a large compatibility method map onto `MainWindow` through class mutation. That mixes layout construction with shell compatibility debt and makes dependencies harder to reason about.

## Scope

- Introduce an explicit desktop shell compatibility boundary for legacy layout methods.
- Preserve the current `MainWindow` public/private method compatibility surface.
- Keep behavior unchanged.
- Add focused tests before production changes.
- Keep the PR under the 400-line review budget.

## Out of scope

- Removing all legacy methods in one PR.
- UI redesign.
- Business logic changes.
- AppState responsibility-separation changes.
- Audio, recommendation, export, storage, or Serato behavior changes.

## Success criteria

- `layout.py` no longer owns the compatibility installer.
- A named shell compatibility module owns the grafting boundary.
- Existing MainWindow callers still find the legacy methods.
- Focused tests and release gate pass.
