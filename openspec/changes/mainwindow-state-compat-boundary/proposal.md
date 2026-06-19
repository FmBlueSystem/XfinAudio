# Proposal: MainWindow State Compatibility Boundary

## Intent
Move legacy `MainWindow.__setattr__` AppState write compatibility out of the UI shell and into an explicit desktop shell compatibility helper.

## Problem
`MainWindow.__setattr__` currently mixes Qt shell behavior, legacy attribute compatibility, AppState field mapping, and service mirroring for scan/recommendation services. That hides a business/state compatibility policy inside the UI class.

## Scope
- Add focused tests that prove legacy attribute writes are handled by an explicit shell compatibility boundary.
- Preserve current write behavior for AppState-backed attributes.
- Keep `MainWindow.__setattr__` as a thin delegator instead of owning the policy.
- Keep behavior visible to users unchanged.

## Out of Scope
- No broad `MainWindow` rewrite.
- No changes to playlist recommendation behavior.
- No audio mutation, DSP, or live Serato DB writes.
- No dependency changes.

## Success Criteria
- Tests prove the compatibility helper owns state-write handling.
- Existing main-window tests still pass.
- Full release gate passes.
- Review diff remains under the 400-line budget.

## Rollback
Revert the helper extraction and restore the inline `__setattr__` body if any compatibility regression appears.
