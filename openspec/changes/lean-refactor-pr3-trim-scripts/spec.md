# Spec: Trim scripts directory

## ADDED Requirements

### Requirement: Dead spectral scripts must be removed

`scripts/benchmark_spectral_analysis.py` and `scripts/validate_spectral_colors.py`
have no callers in the repo and are not referenced by README, CONTRIBUTING, docs, CI,
or the release-gate check. They SHALL be deleted.

#### Scenario: No spectral one-shot scripts

- **WHEN** `git ls-files scripts/benchmark_spectral_analysis.py scripts/validate_spectral_colors.py` is invoked
- **THEN** it returns no entries.

### Requirement: Dead shell launchers must be removed

`scripts/alert_user.sh` and `scripts/xfinaudio-launcher.sh` have no callers and are not
referenced anywhere in the repo's documentation. They SHALL be deleted.

#### Scenario: No undocumented shell launchers

- **WHEN** `git ls-files scripts/alert_user.sh scripts/xfinaudio-launcher.sh` is invoked
- **THEN** it returns no entries.
- **WHEN** `grep -rE "alert_user|xfinaudio-launcher" README.md CONTRIBUTING.md docs/ .github/` is invoked
- **THEN** it returns no hits (this is also the reason to delete).

## MODIFIED Requirements

None.

## REMOVED Requirements

None.

## Invariants

- The two translation scripts (`fill_spanish_translations.py`,
  `update_translations.py`) MUST remain intact and referenced.
- `scripts/release_gate_check.py` and `scripts/source_package_hygiene_check.py`
  MUST NOT be touched.
- `pyproject.toml` MUST NOT change (the `extend-per-file-ignores` for
  `fill_spanish_translations.py` stays valid).
- The release-gate check MUST continue to pass.
