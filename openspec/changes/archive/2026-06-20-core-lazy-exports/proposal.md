# Change: core-lazy-exports

## Intent
Keep pure `library` and `audio` submodule imports isolated by removing eager package-level imports from their package barrels.

## Scope
- Convert `xfinaudio.library` public exports to lazy resolution.
- Convert `xfinaudio.audio` public exports to lazy resolution.
- Add focused import-boundary regression tests in fresh Python processes.
- Preserve existing public package imports.

## Out of scope
- Desktop/UI changes.
- Recommendation behavior changes.
- Export format changes.
- Audio mutation, DSP scope changes, or Serato DB V2 writes.
- Dependency changes.

## Risks
- Callers using `from xfinaudio.library import ...` or `from xfinaudio.audio import ...` must continue to work unchanged.
- Type checkers must still see public symbols without forcing runtime imports.

## Rollback
Revert package `__init__.py` changes and remove import-boundary tests/artifacts.

## Success criteria
- Importing `xfinaudio.library.models` does not load scan services or repositories.
- Importing `xfinaudio.audio.analysis_planning` does not load batch analysis or spectral profile modules.
- Existing public exports from `xfinaudio.library` and `xfinaudio.audio` resolve on demand.
- Full local and CI gates pass.
