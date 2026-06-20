# Tasks: Copilot variant shell bridge explicit

- [x] RED: Update shell compatibility coverage so `_on_copilot_variant_applied` must be explicit and absent from `LEGACY_LAYOUT_METHODS`.
- [x] GREEN: Add the explicit `MainWindow` delegator to `PrepCopilotController.on_variant_applied(index)`.
- [x] GREEN: Remove `_on_copilot_variant_applied` from `LEGACY_LAYOUT_METHODS`, leaving spectral grafts unchanged.
- [x] VERIFY: Run focused shell/Prep Copilot tests and full release gates.
- [x] DOCS: Update architecture docs, apply progress, verify report, and state.
