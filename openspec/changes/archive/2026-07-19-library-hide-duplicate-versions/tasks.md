# Tasks: Hide Duplicate Track Versions in the Library Screen

1. [x] **Proposal** — document intent, scope, success criteria.
2. [x] **Specification** — GIVEN/WHEN/THEN for R1-R6.
3. [x] **Design** — alternatives considered for dedup layer placement and search/dedup ordering; correction history from grill + 5-round adversarial review.
4. [x] **TDD: Title/artist normalization (R1)** — RED (suffix-stripping incl. repeated/mixed-order cases, remix descriptors preserved, artist case/whitespace) → GREEN → REFACTOR.
5. [x] **TDD: Blank/placeholder metadata never groups (R2)** — RED (None, blank, and "—" placeholder cases all treated as singletons) → GREEN → REFACTOR.
6. [x] **TDD: Representative selection (R3)** — RED (completeness, missing-field-count, title-length, path tiebreak ordering) → GREEN → REFACTOR.
7. [x] **TDD: Row-level composition with search (R4)** — RED (dedup only considers currently-visible rows; typing into search doesn't desync `_apply_duplicate_filter` from `_apply_filter`) → GREEN (`_apply_search_and_duplicate_filters` composite wired into both `render()` and `_on_search_changed()`) → REFACTOR.
8. [x] **TDD: UI toggle independence (R5)** — RED (toggle doesn't participate in the Complete/Incomplete/Missing-* mutual exclusion; included in Clear Filters, undo-restore, and active-count) → GREEN → REFACTOR.
9. [x] **TDD: Duplicate-count label (R6)** — RED (label text reflects suppressed-row count, empty when off/zero) → GREEN → REFACTOR.
10. [x] **Verify** — run focused and full verification commands (`uv run pytest -q`, `uv run pyright src tests`, `uv run pytest --cov --cov-fail-under=70 -q`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run python scripts/release_gate_check.py --run`).
11. [x] **Native review** — `gentle-ai review start`/`finalize` per this repo's post-apply governance. 2 lineages: found+fixed 1 CRITICAL (title normalization failed on the motivating screenshot's 3 duplicate titles) plus 6 non-blocking findings (5 fixed, 1 deliberately deferred). Final round approved with receipt `review-193e3a2f9299bd42`. See `apply-progress.md`.
12. [x] **Archive** — merge delta spec into `openspec/specs/`, move this change folder to `openspec/changes/archive/`.
