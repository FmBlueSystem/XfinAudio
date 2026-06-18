# Modular Boundary Inventory Proposal

## Intent

Create a maintainable map of XfinAudio functionality and start separating business policy from PySide6 desktop UI code with unit-tested pure modules.

## Problem

Recent audit evidence shows the desktop layer still owns business/process rules such as recommendation pool policy, Prep Copilot strategy values, export readiness routing, scan/spectral workflow state, and live-assistant transition rules. This makes tests depend on `MainWindow`, Qt widgets, event loops, and mutable `AppState` even when the behavior being checked is business logic.

## Scope

In scope:

- Add a functional inventory grouped by independent modules.
- Define module ownership: business/application/domain vs desktop/UI.
- Move the pure recommendation candidate-pool policy out of `xfinaudio.desktop`.
- Add focused unit tests for strategy-name resolution and recommendation candidate-pool policy.
- Fix the Prep Copilot strategy display-label/internal-name boundary bug through a domain-level resolver.

Out of scope:

- Large UI rewrites.
- Export coordinator extraction.
- AppState reducer migration.
- Live Serato database writes.
- Audio mutation or DSP expansion.

## Success Criteria

- The inventory document identifies each major feature, current owner, target module, tests, and first separation slice.
- Recommendation candidate-pool policy is importable from a non-UI module.
- Prep Copilot accepts internal strategy names and display labels through a tested resolver.
- Focused pytest targets pass.

## Risks

- The worktree already contains a blocked `recommendation-scaling-optimizations` change. This slice must stay small and avoid editing unrelated files.
- Existing UI tests may still fail until the active Prep Copilot bug is fixed.

## Rollback Plan

Remove the new documentation, revert the new recommendation policy module and tests, and restore the old desktop imports.
