# Spec: Remove empty shell layout compatibility surface

## Requirement: Layout graft surface removed

Given all legacy layout methods are now explicit `MainWindow` methods,
When the desktop shell imports,
Then it SHALL NOT import or install `shell_layout_compat` and the facade SHALL NOT reexport layout graft names.

## Requirement: Explicit behavior preserved

Given callers use the former legacy method names on `MainWindow`,
When those methods are accessed,
Then they SHALL remain callable directly on `MainWindow`.
