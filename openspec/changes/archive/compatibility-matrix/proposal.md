# Proposal: Compatibility Matrix

## Intent

Document supported Serato versions and known compatibility limitations in a matrix so users and maintainers can set expectations for fixture-based crate export.

## Scope

- Create `docs/serato-compatibility-matrix.md` with a version/limitation matrix.
- Update `docs/serato-fixture-compatibility.md` to reference the matrix.
- Add a test that verifies the matrix document exists and contains the expected sections.
- Produce SDD/TDD artifacts.

## Success Criteria

- [ ] Compatibility matrix doc exists and contains a table.
- [ ] Doc explains which Serato versions are covered by fixture validation and which are not.
- [ ] Test asserts the matrix content.
- [ ] All verification commands pass.
