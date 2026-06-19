# Proposal: AppState scan recommendation reset boundary

## Intent
Extract scan-dependent recommendation reset rules from desktop UI orchestration into a focused immutable AppState transition helper.

## Problem
Desktop code still owns some AppState reset policy directly when scan-dependent state is cleared. That keeps business/state rules coupled to UI handlers and makes broad `MainWindow` tests carry behavior that should be covered at a pure module boundary.

## Scope
- Add or extend pure AppState transition helpers in `xfinaudio.desktop.app_state_transitions`.
- Move scan/folder-change recommendation reset policy behind that helper.
- Add focused unit tests before production changes.
- Keep desktop code responsible for widget reading, signal handling, and rendering only.

## Out of scope
- No UI redesign.
- No recommendation algorithm changes.
- No export behavior changes.
- No audio mutation, DSP expansion, or Serato DB V2 writes.
- No broad `MainWindow` rewrite.

## Success criteria
- Reset behavior is covered in focused unit tests.
- Desktop orchestration delegates AppState reset decisions to the pure helper.
- Existing UI behavior remains unchanged.
- Full XfinAudio release gate passes.

## Review budget
Target under 400 changed lines. If scope exceeds budget, split before implementation.
