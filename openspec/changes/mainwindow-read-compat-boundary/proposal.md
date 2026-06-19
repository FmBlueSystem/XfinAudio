# Proposal: MainWindow Read Compatibility Boundary

## Intent
Move legacy `MainWindow.__getattr__` read compatibility out of the UI shell and into an explicit desktop shell compatibility helper.

## Problem
`MainWindow.__getattr__` currently mixes delegated toolbar/controller reads, private attribute protection, AppState-backed legacy reads, special AppState field aliases, and scan-service token synchronization directly inside the `MainWindow` class.

## Scope
- Add focused tests that prove legacy read compatibility is owned by `desktop.shell_compat`.
- Preserve current behavior for AppState-backed attributes, delegated toolbar/controller attributes, private attribute protection, and scan-service token synchronization.
- Keep `MainWindow.__getattr__` thin.
- Keep behavior visible to users unchanged.

## Out of Scope
- No broad `MainWindow` rewrite.
- No product behavior changes.
- No audio mutation, DSP, or live Serato DB writes.
- No dependency changes.

## Success Criteria
- Tests prove the compatibility helper owns legacy read handling.
- Existing main-window tests still pass.
- Full release gate passes.
- Review diff remains under the 400-line budget.

## Rollback
Revert the helper extraction and restore the inline `__getattr__` body if any compatibility regression appears.
