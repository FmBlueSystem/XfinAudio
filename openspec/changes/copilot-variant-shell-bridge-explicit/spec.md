# Spec: Copilot variant shell bridge explicit

## Requirement: Explicit Copilot variant bridge

Given the desktop build screen connects to `window._on_copilot_variant_applied`,
When the shell compatibility layer is loaded,
Then `_on_copilot_variant_applied` SHALL exist directly on `MainWindow` and SHALL NOT be dynamically installed from `LEGACY_LAYOUT_METHODS`.

## Requirement: Behavior preservation

Given a Prep Copilot variant is applied,
When `_on_copilot_variant_applied(index)` is invoked,
Then `PrepCopilotController.on_variant_applied(index)` SHALL handle the event without changing visible behavior.
