# Proposal: AppState Prep Copilot variant transition boundary

## Intent
Extract Prep Copilot applied-variant AppState update rules from desktop controller mutation into a pure transition helper.

## Problem
`PrepCopilotController.apply_selected_variant()` currently mutates recommendation, explanation, quality, readiness, removed paths, and applied variant state directly. That keeps state-transition policy coupled to desktop UI orchestration.

## Scope
- Add a pure AppState transition helper for applying a Prep Copilot variant result.
- Keep `PrepCopilotController` responsible for selection validation, rendering, status messages, and UI labels.
- Add focused unit tests before production code changes.

## Out of scope
- No Prep Copilot algorithm changes.
- No UI redesign or copy changes.
- No export behavior changes.
- No audio mutation, DSP expansion, or Serato DB V2 writes.

## Success criteria
- Applied-variant state changes are covered by focused unit tests.
- Desktop controller delegates AppState transition policy to the helper.
- Existing Prep Copilot UI behavior and export naming remain unchanged.
- Full release gate passes.
