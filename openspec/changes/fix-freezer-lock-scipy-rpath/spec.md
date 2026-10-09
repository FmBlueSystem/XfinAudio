# Spec delta: freezer lock must freeze audit-clean

## MODIFIED Requirement: packaging locks (freezer environment)

The freezer lock set (`uv.lock` runtime closure, `desktop-electron/requirements-headless.txt`,
`packaging/linux/requirements-build.txt`) SHALL resolve the numeric stack to versions whose
macOS arm64 wheels freeze into a bundle that passes
`packaging/macos/dependencies.audit_tree` without relocation errors.

### Scenario: DMG freeze passes the native audit

- WHEN `packaging/macos/build.py` runs on macOS arm64 with a freezer environment synced from
  `packaging/macos/requirements-build.txt`
- THEN the post-freeze audit completes without `Runtime rpath escapes bundle`,
  `Runtime retains an absolute non-system rpath` or
  `Runtime retains an absolute non-system install ID` for any collected dylib.

### Scenario: lock consistency is preserved

- WHEN the drift guard `tests/test_headless_requirements_lock_drift.py` runs
- THEN the exported headless file and the compiled Linux lock still match the `uv.lock`
  closure in membership, version and hash (existing guard, unchanged).
