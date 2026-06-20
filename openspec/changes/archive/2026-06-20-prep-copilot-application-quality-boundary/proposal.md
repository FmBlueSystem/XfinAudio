# Prep Copilot Application Quality Boundary

## Intent
Move Prep Copilot variant application orchestration out of the desktop controller and into the application layer so the UI applies and renders an already-built application result.

## Scope
- Add an application-level use case for applying a Prep Copilot variant.
- The application use case builds the playlist explanation and quality report for the selected variant, preserving the variant readiness report.
- Make the desktop Prep Copilot controller depend on the application boundary instead of calculating quality directly.
- Add focused tests for application orchestration and desktop delegation.

## Out of Scope
- No changes to Prep Copilot variant generation, scoring, ranking, or readiness rules.
- No export workflow, Serato format, or live Serato DB V2 changes.
- No DSP, audio mutation, waveform, BPM/key detection, or audio rendering.

## Risks
- If only imports move, the UI can remain coupled to business decisions.
- Rendering order must remain stable after the selected variant is applied.

## Rollback Plan
Revert the application use case and restore direct desktop calls to `build_playlist_explanation` and `build_quality_report`.

## Success Criteria
- The application layer exposes a testable Prep Copilot variant application use case.
- The desktop controller delegates selected-variant business orchestration through an injected application callable.
- Existing UI behavior remains intact and gates pass.
