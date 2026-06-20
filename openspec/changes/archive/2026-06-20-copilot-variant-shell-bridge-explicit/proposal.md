# Proposal: Copilot variant shell bridge explicit

## Intent

Move `_on_copilot_variant_applied` out of dynamic layout grafting and make it an explicit `MainWindow` method.

## Scope

In:
- Add RED coverage proving `_on_copilot_variant_applied` is a direct `MainWindow` method and absent from `LEGACY_LAYOUT_METHODS`.
- Add the explicit delegator to `PrepCopilotController.on_variant_applied(index)`.
- Remove the graft-map entry for `_on_copilot_variant_applied`.
- Update architecture docs and SDD evidence.

Out:
- No behavior changes to Prep Copilot variant application.
- No spectral completion changes.
- No removal of remaining layout helpers beyond the graft-map entry.

## Success Criteria

- `_on_copilot_variant_applied` is callable as a direct `MainWindow` method.
- `LEGACY_LAYOUT_METHODS` count decreases from 6 to 5.
- Prep Copilot variant behavior remains covered by focused tests.
- Full release gates pass.

## Safety

No audio mutation, DSP expansion, live Serato DB V2 writes, or dependency changes.
