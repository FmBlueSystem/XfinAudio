# Proposal: No Unsafe Live Serato Writes

## Intent

Close the remaining P0 release blocker by making it explicit in UI copy and release notes that live Serato writes are not part of the verified release candidate. The functionality remains available, but the user is clearly warned to back up and verify any live library interaction.

## Scope

### In Scope

- Update Export screen copy in `export_view_model.py` and `export_screen.py`.
- Reinforce `docs/release-notes-template.md` with the live-write boundary.
- Add tests that lock in the warning text.
- Produce SDD/TDD artifacts.

### Out of Scope

- Removing or disabling Serato export.
- Changing export coordinators or file formats.
- Adding new product features.
- Updating translation files.

## Capabilities

- `no-unsafe-live-writes`: Clear communication that live Serato writes are not verified as part of the release candidate.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/xfinaudio/desktop/export_view_model.py` | Modified | Warning text in export guidance/destination. |
| `src/xfinaudio/desktop/screens/export_screen.py` | Modified | Default guidance label warning. |
| `docs/release-notes-template.md` | Modified | Reinforced live-write boundary. |
| `tests/test_export_view_model.py` | Created/Modified | Asserts warning text. |
| `openspec/changes/no-unsafe-live-writes/` | Created | SDD/TDD artifacts. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Tests become brittle on wording | Low | Assert on stable key phrases. |
| Translations drift | Low | Do not modify `.ts` files. |

## Success Criteria

- [ ] Export screen copy warns about live Serato writes not being part of the RC.
- [ ] Release notes template reinforces the same warning.
- [ ] Tests assert the warning text.
- [ ] All verification commands pass.
