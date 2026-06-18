# Design: Trim scripts directory

## Approach

Pure deletion of 4 files with verified-zero callers. The two translation scripts
remain. No source code, no test, no dependency changes. No replacement — git history
preserves the deleted files for any future revival.

## Files affected

| Path                                       | Status  | Lines | Reason |
|--------------------------------------------|---------|-------|--------|
| `scripts/benchmark_spectral_analysis.py`   | tracked | 360   | one-shot, no caller, no CI |
| `scripts/validate_spectral_colors.py`      | tracked | 96    | one-shot, no caller, no CI |
| `scripts/alert_user.sh`                    | tracked | 16    | bash, no caller, no docs |
| `scripts/xfinaudio-launcher.sh`            | tracked | 18    | bash, no caller, no docs |

Total: ~490 LOC removed, 4 files.

## Verification of zero-callers (must be re-run by apply)

- `grep -rE "benchmark_spectral_analysis" --include="*.py" --include="*.md" --include="*.yaml" --include="*.yml" --include="*.sh" .` → only the file itself.
- `grep -rE "validate_spectral_colors" --include="*.py" --include="*.md" --include="*.yaml" --include="*.yml" --include="*.sh" .` → only the file itself.
- `grep -rE "alert_user" --include="*.py" --include="*.md" --include="*.yaml" --include="*.yml" --include="*.sh" --include="*.github" .` → only the file itself.
- `grep -rE "xfinaudio-launcher" --include="*.py" --include="*.md" --include="*.yaml" --include="*.yml" --include="*.sh" --include="*.github" .` → only the file itself.

## Step-by-step

1. Pre-flight grep as above. If any unexpected hit, STOP and report.
2. `git rm scripts/benchmark_spectral_analysis.py scripts/validate_spectral_colors.py scripts/alert_user.sh scripts/xfinaudio-launcher.sh`
3. Verify:
   - `git ls-files scripts/benchmark_spectral_analysis.py scripts/validate_spectral_colors.py scripts/alert_user.sh scripts/xfinaudio-launcher.sh` → empty.
   - `ls scripts/fill_spanish_translations.py scripts/update_translations.py` → both present.
   - `uv run pytest -q` → green.
   - `uv run ruff check .` → green.
   - `uv run pyright src tests` → green.
4. Single work-unit commit: `chore(scripts): remove dead spectral and shell scripts`.

## Risks

- **Undocumented user habit**: a developer might have been running the deleted
  sh scripts from muscle memory. Recovery path: `git log -- scripts/xfinaudio-launcher.sh`
  to find the commit, then `git show <sha>:scripts/xfinaudio-launcher.sh > scripts/xfinaudio-launcher.sh`
  to restore. The PR body will document this.

## Rollback

Single `git revert <commit-sha>` restores the previous state.
