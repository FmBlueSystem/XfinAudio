# DJ Readiness Application Boundary

## Intent
Move DJ readiness report orchestration out of the desktop controller and into the application layer so the UI only renders an already-built application result.

## Scope
- Add an application-level DJ readiness use case.
- Make the desktop DJ readiness controller depend on the application boundary instead of calling quality report construction directly.
- Preserve existing report semantics, Serato validation behavior, and UI labels/tables.
- Add focused tests proving the boundary and controller delegation.

## Out of Scope
- No changes to DJ readiness scoring rules.
- No changes to Serato crate formats or live Serato DB V2 writes.
- No DSP, audio mutation, waveform, BPM/key detection, or audio rendering.
- No broad MainWindow or export workflow rewrite.

## Risks
- Desktop and quality imports can remain coupled if only import paths change cosmetically.
- UI behavior can regress if the controller no longer stores and renders the report in the same sequence.

## Rollback Plan
Revert the new application module and restore the controller's direct call to `build_dj_readiness_report`.

## Success Criteria
- The application layer exposes a testable DJ readiness use case.
- The desktop controller delegates report creation through an injected application callable.
- Existing DJ readiness behavior and full gates remain green.
