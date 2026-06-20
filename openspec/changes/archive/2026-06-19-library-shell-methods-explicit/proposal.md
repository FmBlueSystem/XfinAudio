# Proposal: Library shell methods explicit on MainWindow

## Intent
Reduce `shell_layout_compat` dynamic method grafting by moving the smallest Library-owned shell method group onto explicit `MainWindow` methods.

## Problem
`MainWindow` still receives many methods dynamically through `shell_layout_compat.install_legacy_layout_methods()`. Two of those methods, `choose_folder` and `_refresh_idle_action_state`, already have clear LibraryController ownership. Keeping them in the graft map hides a real dependency and delays removal of the compatibility surface.

## Scope
In scope:
- Add focused RED coverage proving the Library shell methods are not installed through `LEGACY_LAYOUT_METHODS`.
- Add explicit `MainWindow.choose_folder()` and `MainWindow._refresh_idle_action_state()` methods that delegate to the LibraryController.
- Remove `choose_folder` and `_refresh_idle_action_state` from `shell_layout_compat.LEGACY_LAYOUT_METHODS`.
- Preserve visible behavior and remaining legacy layout grafting.
- Update architecture documentation.

Out of scope:
- Removing `shell_layout_compat` entirely.
- Migrating unrelated layout, recommendation, export, or scan methods.
- Product behavior changes, audio mutation, DSP, dependency changes, or Serato DB V2 writes.

## Success criteria
- The selected methods remain callable on `MainWindow`.
- The selected methods are absent from `LEGACY_LAYOUT_METHODS`.
- Existing shortcuts and screen signal wiring continue to call the same public `MainWindow` method names.
- Focused and full verification gates pass.
- Review size stays below 400 changed lines.

## Rollback
Re-add the selected method names to `shell_layout_compat.LEGACY_LAYOUT_METHODS` and remove the explicit `MainWindow` delegators.
