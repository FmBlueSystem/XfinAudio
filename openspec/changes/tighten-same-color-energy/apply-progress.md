# Apply Progress: Tighten Same Color & Energy

Strict TDD is active. This file tracks per-slice implementation progress.

## Slice PR 1 — Phase 1: Characterization Safety Net (NO behavior change)

Scope: pin the CURRENT behavior of untouched code so later slices prove they did
not break it. Zero production behavior changed in this slice.

### Completed Tasks

- [x] 1.1 Characterize `_apply_energy_tolerance()` (`playlist_service.py:766-787`)
- [x] 1.2 Characterize shared `_apply_color_filter()` `same_color` fallback (`playlist_service.py:689-704`)
- [x] 1.3 Characterize current `same_color` / `same_energy` / `same_color_energy` descriptions + registration
- [x] 1.4 VERIFY Phase 1 green (`uv run pytest -q`)

### Files Changed

| File | Action | What was done |
|------|--------|---------------|
| `tests/test_playlist_service.py` | Modified | Added 6 characterization tests for `_apply_energy_tolerance` (`+/-1` band, `preserve_paths` bypass, `tolerance is None` passthrough, no-removal warningless case) and shared `_apply_color_filter` `same_color` unfiltered fallback + exact warning strings. Imported the two private functions. |
| `tests/test_playlist_strategies.py` | Modified | Added 3 verbatim characterization tests pinning current `same_color`, `same_energy`, and `same_color_energy` descriptions + weights/tolerance/display names. |

No production source files were modified in this slice (spec boundary honored).

### TDD Cycle Evidence

Characterization suites pin CURRENT behavior, so the correct RED->GREEN evidence
is: the test must pass against today's code on first run. If it had failed, the
test (not production) would have been corrected to match reality.

| Task | RED (test written first) | GREEN (passes against today's code) | Notes |
|------|--------------------------|-------------------------------------|-------|
| 1.1 | Added `_apply_energy_tolerance` characterization tests | PASS on first run against unchanged production | No production edit |
| 1.2 | Added `_apply_color_filter` fallback characterization tests | PASS on first run against unchanged production | No production edit |
| 1.3 | Added verbatim description characterization tests | PASS on first run against unchanged production | No production edit |

All characterization assertions matched current behavior exactly on the first
run (9/9), confirming the pinned understanding of current behavior is correct.

### Work Unit Evidence

| Evidence | Value |
|----------|-------|
| Focused test command | `uv run pytest -q tests/test_playlist_service.py tests/test_playlist_strategies.py` -> `126 passed` |
| Characterization subset | `-k "characteriz or verbatim or apply_energy_tolerance or apply_color_filter or currently_verbatim"` -> `9 passed, 117 deselected` |
| Runtime harness | N/A — this slice adds unit-level characterization tests only; no runtime/integration boundary is crossed. |
| Rollback boundary | Delete the two appended characterization test blocks (and the two added imports in `tests/test_playlist_service.py`). No production code to revert. |

### Full Verification (exact order)

| # | Command | Result |
|---|---------|--------|
| 1 | `uv run pytest -q` | PASS — `1431 passed` |
| 2 | `uv run pyright src tests` | PASS — `0 errors, 0 warnings, 0 informations` |
| 3 | `uv run pytest --cov --cov-fail-under=70 -q` | PASS — `Total coverage: 91.34%`, `1431 passed` |
| 4 | `uv run ruff check .` | PASS — `All checks passed!` |
| 5 | `uv run ruff format --check .` | PASS — `281 files already formatted` |
| 6 | `uv run python scripts/release_gate_check.py --run` | PASS — exit 0 |

### Discovery While Characterizing

- `_apply_color_filter()` and `_apply_energy_tolerance()` had NO covering tests
  before this slice despite two callers each; that gap is exactly why the
  characterization slice exists. They are now pinned.
- On first full-suite run, `tests/test_public_open_source_docs.py` failed with
  `FileNotFoundError: AGENTS.md`. Root cause: a stray UNCOMMITTED working-tree
  deletion of `AGENTS.md` that pre-existed this slice (not committed to the
  tracker branch, not caused by these tests). Restoring `AGENTS.md`
  (`git checkout -- AGENTS.md`) made the docs tests pass. That deletion is out of
  this slice's scope and was not carried into the commit.

### Remaining (later slices, OUT of this slice's scope)

- [ ] Phase 2-7: strict combined eligibility, anchor identity, fail-closed
      warnings, strategy description, public-API/anchor protection, desktop
      wiring, final verification.
