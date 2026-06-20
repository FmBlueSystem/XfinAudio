# Change: application-lazy-exports

## Intent
Keep application submodule imports isolated by removing eager package-level imports from `xfinaudio.application`.

## Scope
- Convert `xfinaudio.application` public package exports to lazy resolution.
- Add focused import-boundary regression tests in fresh Python processes.
- Preserve existing public package imports.

## Out of scope
- Desktop/UI changes.
- Workflow behavior changes.
- Recommendation, export, DSP, audio mutation, or Serato DB V2 changes.
- Dependency changes.

## Success criteria
- Importing a pure application submodule does not load sibling workflow/export modules as package-import side effects.
- Existing public `from xfinaudio.application import ...` imports still resolve.
- Full local and CI gates pass.
