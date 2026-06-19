# Proposal: AppState Prep Copilot plan transition boundary

## Intent
Extract Prep Copilot plan set/clear AppState updates from desktop controller mutation into pure transition helpers.

## Problem
`PrepCopilotController.generate()` directly clears or stores `last_prep_copilot_plan`. That keeps state update policy coupled to UI orchestration.

## Scope
- Add pure helpers for storing and clearing the Prep Copilot plan.
- Keep `PrepCopilotController` responsible for selection validation, rendering, buttons, and status messages.
- Add focused unit tests before production changes.

## Out of scope
- No Prep Copilot algorithm changes.
- No UI redesign or copy changes.
- No audio mutation, DSP expansion, or Serato DB V2 writes.

## Success criteria
- Plan set/clear state changes are covered by focused tests.
- Desktop controller delegates AppState plan updates to pure helpers.
- Existing Prep Copilot generation behavior remains unchanged.
- Full release gate passes.
