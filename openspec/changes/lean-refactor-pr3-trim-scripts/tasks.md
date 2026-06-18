# Tasks: Trim scripts directory

Strict TDD applies. This change is deletion-only with no behavioral surface. The
"tests" are the existing pytest/ruff/pyright suite and the release-gate check.

## 1. Pre-flight grep

- [x] `grep -rE "benchmark_spectral_analysis|validate_spectral_colors|alert_user|xfinaudio-launcher" --include="*.py" --include="*.md" --include="*.yaml" --include="*.yml" --include="*.sh" --include="*.json" --include="*.toml" .` excluding `.git/`, `openspec/changes/`, and the files being deleted.
- [x] Acceptance: zero hits in any file other than the four slated for deletion.

## 2. Delete the four scripts

- [x] `git rm scripts/benchmark_spectral_analysis.py scripts/validate_spectral_colors.py scripts/alert_user.sh scripts/xfinaudio-launcher.sh`

## 3. Verify

- [x] `git ls-files scripts/benchmark_spectral_analysis.py scripts/validate_spectral_colors.py scripts/alert_user.sh scripts/xfinaudio-launcher.sh` → empty.
- [x] `ls scripts/fill_spanish_translations.py scripts/update_translations.py` → both present.
- [x] `uv run pytest -q` → green.
- [x] `uv run ruff check .` → green.
- [x] `uv run pyright src tests` → green.

## 4. Commit and merge

- [x] One work-unit commit: `chore(scripts): remove dead spectral and shell scripts`.
- [x] Push the branch.
- [x] Open PR against `tracker/lean-refactor`.
- [x] Update state.yaml → state: verifying, apply: complete.
- [x] Write apply-progress.md.
- [ ] After PR 3 merges, branch off the updated tracker for PR 4
  (`refactor/collapse-desktop-services`).
