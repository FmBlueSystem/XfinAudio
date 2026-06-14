# Proposal: Scan Settings Review

## Intent

Make scan options and metadata field mappings visible on the Library screen before the user starts a long scan, satisfying the P1 backlog item.

## Scope

### In Scope

- Add a pure ViewModel method that builds a concise scan settings review string.
- Add a read-only label on the Library screen.
- Wire the label through the existing render path.
- Add tests for the ViewModel method and UI label.
- Produce SDD/TDD artifacts.

### Out of Scope

- Changing scan algorithms or audio handling.
- Adding persistence or settings schema changes.
- Large UI redesign.
- Updating translation files.

## Capabilities

- `scan-settings-review`: Users can see supported extensions and required metadata field mappings before scanning.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/xfinaudio/desktop/library_view_model.py` | Modified | New `scan_settings_review_text` method. |
| `src/xfinaudio/desktop/screens/library_screen.py` | Modified | New `scan_settings_label` and render update. |
| `tests/test_library_view_model.py` | Modified/created | Tests for review text. |
| `tests/test_library_screen.py` | Modified/created | Tests for label rendering. |
| `openspec/changes/scan-settings-review/` | Created | SDD/TDD artifacts. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| UI label crowds the screen | Low | Keep text concise. |
| Tests become brittle | Low | Assert on stable field/extension names. |

## Success Criteria

- [ ] Library screen shows supported extensions and metadata mappings.
- [ ] `scan_settings_review_text` is pure and tested.
- [ ] All verification commands pass.
