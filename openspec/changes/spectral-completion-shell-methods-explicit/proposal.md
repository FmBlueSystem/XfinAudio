# Proposal: Spectral completion shell methods explicit

## Intent

Move the five remaining spectral completion shell methods out of dynamic layout grafting and make them explicit `MainWindow` methods.

## Scope

In:
- Add RED coverage proving the five spectral completion methods are explicit `MainWindow` methods and absent from `LEGACY_LAYOUT_METHODS`.
- Add explicit delegators to `LibraryController` for start, cancel, progress, profile-ready, and completion events.
- Remove all remaining entries from `shell_layout_compat.LEGACY_LAYOUT_METHODS`.
- Update architecture docs and SDD evidence.

Out:
- No worker lifecycle redesign.
- No spectral algorithm or DSP changes.
- No audio mutation.

## Success Criteria

- The spectral completion methods are callable as direct `MainWindow` methods.
- `LEGACY_LAYOUT_METHODS` is empty after this slice.
- Existing spectral completion behavior tests continue to pass.
- Full release gates pass.
