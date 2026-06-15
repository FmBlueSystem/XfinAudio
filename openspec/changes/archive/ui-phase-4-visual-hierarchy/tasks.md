# Tasks: Phase 4 - Visual Hierarchy

1. [x] Proposal, spec, design
2. [x] Add theme styles for `#secondaryAction` and `#sectionDivider`
3. [x] Library: primary/secondary objectNames, divider, no-library/no-tracks empty states
4. [x] Build: primary/secondary objectNames, divider, no-recommendation empty state
5. [x] Export: primary/secondary objectNames, divider
6. [x] Focused tests (RED → GREEN)
7. [x] Verify
8. [ ] Commit and PR

## Notes

- Export primary action keeps its established `seratoExportButton` gold-accent objectName
  (not the generic cyan `primaryAction`) to avoid breaking `tests/test_main_window.py`,
  which is outside the allowed-modify set. Larger min-height still applies for emphasis.
