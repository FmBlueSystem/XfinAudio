# Archive Report: Strategy UX Clarity and Duplicate Dedupe

**Change**: `strategy-ux-clarity-and-dedupe`  
**Archived**: 2026-07-20  
**Archive Path**: `openspec/changes/archive/2026-07-20-strategy-ux-clarity-and-dedupe/`  
**Artifact Store**: openspec (hybrid with Engram persistence)

---

## What Shipped

### Slices Delivered

**Slice A (PR #303, commit e403482)** — Strategy Selection UX  
Two chained items addressing stale strategy descriptions and internal-name display:
1. Immediate label refresh on strategy combo selection (no re-render required)
2. Display names in combo, with internal names preserved as item data; emitted and persisted values stay internal

**Slice B (PR #304, commit 169022f)** — Recommendation Pool Dedupe  
Duplicate-version suppression with maintainer-decided aggressive playlist-level grouping:
1. Candidate pool keeps one representative per duplicate group
2. Playlist-level key ignores parenthetical descriptors (aggressive); Library filter retains conservative key (unchanged)
3. Control tracks (locked, start, end, manual) never removed by dedupe
4. Two CRITICAL boundary-condition fixes applied via bounded correction (review-c8b72a193ac5d41f)

### Specs Synced to Main Specs

Both delta specs merged byte-identical as new main specs (no pre-existing specs):

| Domain | Action | Path |
|--------|--------|------|
| strategy-selection-ux | Created (from delta) | `openspec/specs/strategy-selection-ux/spec.md` |
| recommendation-duplicate-version-dedupe | Created (from delta) | `openspec/specs/recommendation-duplicate-version-dedupe/spec.md` |

---

## Verification Verdict

**PASS WITH NOTES** — 2026-07-19  
**Scope**: Merged `main` (PR #303 + PR #304 with Slice B delta + bounded correction)

| Metric | Result |
|--------|--------|
| Pytest | 1201 passed in ~27s |
| Pyright | 0 errors, 0 warnings, 0 informations |
| Coverage | 90.76% (required 70%) |
| Ruff | All checks passed |
| Release gate | All gates PASS |

**Severity Summary**:
- CRITICAL issues: 0
- WARNING (doc alignment): 3 — all resolved at archive
- SUGGESTION (optional): 1

### Resolved Warnings (Archive-Time Alignment)

1. **design.md Decision 3b superseded**: Added "Superseded (2026-07-20)" subsection recording maintainer's playlist-level key decision, implementation details, and Library filter invariant.
2. **apply-progress.md correction batch**: Appended "Bounded Correction Batch" section with RED-before-GREEN evidence for both CRITICAL fixes (incomplete-record loss, fully-parenthetical collision).
3. **size:exception acceptance**: Recorded in state.yaml; merged PRs confirm all tests green and production code remains modest.

---

## Implementation Summary

### Production Code (Total 274 lines)

**Slice A** (~85 lines):
- `build_screen.py`: new slot + signal wiring, display-name items, immediate refresh
- `recommendation_service.py`: `currentData()` reads via `findData()`

**Slice B** (~189 lines, including delta):
- `library/duplicate_grouping.py` (NEW, 158 lines): neutral normalization + conservative key + playlist key + representative sort
- `desktop/library_filter.py`: delegation to neutral helpers (imports only)
- `recommendation/candidate_pool.py`: `dedupe_recommendation_duplicates` with complete-only grouping + control immunity
- `recommendation/controls.py`: promoted `preserved_control_paths`
- `application/recommendation_candidates.py`: dedupe wiring before 25-cap
- `playlist_service.py`: uses promoted preserved_control_paths

### Test Coverage (Total 518+ lines)

**Slice A** (~190 lines):
- `test_build_screen.py`: combo display-name, immediate refresh, end-to-end emission
- `test_recommendation_service_state.py`: `currentData()` reads, `findData()` selection
- `test_main_window.py`: combo-text updates for display labels

**Slice B** (~328+ lines, including delta):
- `test_duplicate_grouping.py` (289 lines): neutral normalization, group-key parametrization, conservative vs. playlist key contrast, fully-parenthetical singleton guard
- `test_candidate_pool.py` (320 lines): dedupe collapse, control immunity, determinism, no-duplicates pass-through, three live-observed pairs verbatim
- `test_application_recommendation_candidates.py`: dedupe before cap wiring
- `test_library_filter.py` (zero edits, 39 tests green): display filter regression guard

---

## Bounded Correction (Lineage `review-c8b72a193ac5d41f`)

Native 4R post-implementation review identified and fixed two CRITICAL boundary conditions:

### CRITICAL 1: Incomplete Record Loss
- **Issue**: Incomplete records grouped with complete siblings could suppress the complete track.
- **Fix**: Group only `metadata_status == "complete"` records; incomplete pass through unchanged.
- **Evidence**: RED test `test_plan_recommendation_candidates_does_not_lose_complete_track_to_incomplete_locked_duplicate` failed pre-fix (returned empty pool), passes post-fix (complete track included).
- **Lines**: `candidate_pool.py:153-155` (3 lines) + docstring rationale.

### CRITICAL 2: Fully-Parenthetical Collision
- **Issue**: Titles consisting entirely of parentheticals (e.g., `"(Intro)"`) normalized to empty string, colliding with each other.
- **Fix**: Singleton guard in `playlist_duplicate_group_key`: empty normalized title returns `None` (no grouping).
- **Evidence**: RED tests failed pre-fix; both now pass:
  - `test_playlist_duplicate_group_key_none_when_normalized_title_is_fully_parenthetical`
  - `test_dedupe_does_not_collapse_distinct_fully_parenthetical_titles`
- **Lines**: `duplicate_grouping.py:132-137` (6 lines singleton guard).

**Total bounded correction delta**: 78 lines (17 production + 61 test).

---

## Task Completion

- **Slice A tasks A1–A16**: 16/16 [x] — all checked
- **Slice B tasks B1–B15**: 15/15 [x] — all checked
- **Characterization and regression guards**: All present and passing
- **RED-before-GREEN evidence**: Documented in apply-progress.md for all three segments (Slice A, Slice B, correction batch)

---

## Review Lineages

| Lineage | Scope | Result | Notes |
|---------|-------|--------|-------|
| `review-8ac8e0c55f04e362` | Slice A UI | Approved | Native 4R gate; all spec requirements met |
| `review-c8b72a193ac5d41f` | Slice B dedupe + correction | Approved with correction | 2 CRITICAL findings fixed via bounded correction; both present in merged tree with asserting tests |

---

## Follow-Up Items

### Closed at Archive
1. **design.md Decision 3b Superseded**: Maintainer playlist-key decision now documented (2026-07-20).
2. **apply-progress.md Correction Batch**: Two CRITICAL fixes with RED-before-GREEN evidence recorded.
3. **size:exception Acceptance**: Verified and recorded (post-delta 980 total, production code modest).

### Open (Non-Blocking)

1. **Test file organization** (SUGGESTION): `test_candidate_pool.py` grew to 320 lines; consider splitting if it grows further (organizational only, no correctness risk).

2. **Incomplete-vs-incomplete dedupe asymmetry** (DISCOVERY): Current design groups only complete records and passes incomplete through unchanged. This is correct but means two incomplete duplicates will NOT collapse. This is a deliberate trade-off to avoid silent complete-record loss (CRITICAL 1). Documented in apply-progress.md; may warrant future review if user workflows require incomplete deduplication.

3. **Stale dev script** (DEV): `tests/integration_flow.py` (not collected by pytest) has two distinct stale items: line 9 hardcodes a `sys.path` to an unrelated checkout, and line 235 still selects the strategy combo by internal name (`setCurrentText("harmonic_journey")`), which no longer matches an item after Slice A switched combo item text to display names. Out of scope for this change; align or delete the script in a future cleanup.

---

## Final Checklist

- [x] All tasks marked complete in `tasks.md` (A1–A16, B1–B15)
- [x] Verify verdict PASS WITH NOTES resolved (3 WARNINGs, 1 SUGGESTION)
- [x] Both CRITICAL corrections present in merged tree with asserting tests
- [x] Delta specs merged to main specs (2 new specs)
- [x] Archive folder created with all artifacts
- [x] state.yaml updated (status: archive, archived_at: 2026-07-20)
- [x] Archive-report.md written with full traceability

---

## Archive Metadata

- **Proposed**: 2026-07-18
- **Specs**: 2026-07-18
- **Design**: 2026-07-18
- **Tasks**: 2026-07-18
- **Applied**: 2026-07-19 (Slice A + Slice B with delta)
- **Verified**: 2026-07-19
- **Archived**: 2026-07-20

**SDD Cycle Status**: COMPLETE — Change fully planned, implemented, verified, and archived.
