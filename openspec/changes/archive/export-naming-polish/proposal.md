# Proposal: Export Naming Polish

## Intent

Make default non-Serato export filenames include the recommendation strategy and a filesystem-safe timestamp, matching the naming polish already present in Serato crate exports.

## Scope

### In Scope

- Create `src/xfinaudio/exporting/export_naming.py` utility.
- Update `src/xfinaudio/desktop/export_coordinator.py` to use it for Rekordbox, Traktor, and VirtualDJ exports.
- Add `tests/test_export_naming.py`.
- Update `tests/test_export_coordinator.py` if it asserts default filenames.
- Produce SDD/TDD artifacts.

### Out of Scope

- Serato crate naming (already polished).
- New export formats.
- UI changes.
- Translation updates.

## Capabilities

- `export-naming-polish`: Default export filenames are descriptive, collision-resistant, and filesystem-safe.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/xfinaudio/exporting/export_naming.py` | Created | New filename generation utility. |
| `src/xfinaudio/desktop/export_coordinator.py` | Modified | Uses new utility for default names. |
| `tests/test_export_naming.py` | Created | Unit tests for filename generation. |
| `tests/test_export_coordinator.py` | Modified | Updated filename expectations if needed. |
| `openspec/changes/export-naming-polish/` | Created | SDD/TDD artifacts. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Existing tests assert old default name | Medium | Update expectations as part of change. |
| Filenames too long | Low | Keep compact format. |

## Success Criteria

- [ ] Default non-Serato filenames include timestamp and strategy name.
- [ ] Filenames are filesystem-safe.
- [ ] Tests assert the new pattern.
- [ ] All verification commands pass.
