# Proposal: Split Shell Compatibility Surfaces

## Intent
Split the temporary desktop shell compatibility module into clearer compatibility surfaces so each legacy concern can be reviewed and retired independently.

## Problem
`desktop/shell_compat.py` now mixes layout method grafting, MainWindow AppState read/write compatibility, delegated UI reads, and missing-attribute sentinel handling. This is safer than keeping the logic inside `MainWindow`, but it is still a mixed responsibility module.

## Scope
- Add focused tests that require separate layout and state compatibility modules.
- Move legacy layout method grafting into a layout compatibility module.
- Move legacy AppState read/write compatibility into a state compatibility module.
- Preserve a thin `shell_compat` facade for existing imports.
- Preserve visible app behavior.

## Out of Scope
- No broad `MainWindow` rewrite.
- No product behavior changes.
- No audio mutation, DSP, or live Serato DB writes.
- No dependency changes.

## Success Criteria
- Tests prove separate compatibility modules exist and own their surfaces.
- Existing shell and main-window tests still pass.
- Full release gate passes.
- Review diff remains under the 400-line budget.

## Rollback
Revert to the prior single `shell_compat.py` module if any compatibility regression appears.
