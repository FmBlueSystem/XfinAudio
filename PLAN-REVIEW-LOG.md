# Plan Review Log: Hide duplicate track versions in the Library screen
Act 1 (grill) complete — plan locked with the user. MAX_ROUNDS=5.
Reviewer model: gpt-5.6-sol (config default, reasoning effort: low) — codex-cli 0.144.6.

## Round 1 — Codex

1. BUG — search runs later (library_screen_rendering.py:207-217), after tracks_for_display; dedup could hide the only version matching a search query.
2. BUG — TrackRecord.title/artist are nullable; normalizing them to empty strings could collapse unrelated incomplete tracks into one group.
3. BUG — order-dependent suffix removal: "Song - 8A - Energy 7 (v2)" survives partially if suffixes aren't stripped repeatedly.
4. RISK — no TDD/OpenSpec artifacts despite mandatory repository governance.
5. RISK — new button omits established tooltip/accessibility/tab-order contracts other buttons follow.
6. RISK — status_text() still reports the raw scanned-record count; no indication of how many duplicates are hidden.

VERDICT: REVISE

### Claude's response
- Finding 1: verified and found MORE severe than stated — traced the full render() call chain and confirmed LibraryFilters.search_query is dead code in production (_current_library_filters never populates it); the ENTIRE live search is the row-level _apply_filter(). Since it runs on already-rendered rows, dedup done at the data layer (inside tracks_for_display, before rows are ever rendered) would make a suppressed duplicate's row permanently unfindable by search, not just transiently. Fixed by moving dedup entirely to a new row-level pass, _apply_duplicate_filter(), running after _apply_filter() in render() — so it only ever operates on rows that already survived search. Dropped the LibraryFilters.hide_duplicates/library_filters_from_flags plumbing from the original draft since it's no longer the right layer.
- Finding 2: verified (library/models.py:20-21, both str | None) — accepted. Added an explicit None/blank guard in _duplicate_group_key that treats such rows as singletons, never grouped.
- Finding 3: accepted — normalization now strips suffixes in a loop until stable, not a single pass.
- Finding 4: accepted, consistent with this session's established precedent (Codex won this argument earlier for the recommendation-engine change) — will create openspec/changes/library-hide-duplicate-versions/ artifacts before/alongside implementation.
- Finding 5: verified real (_setup_button_tooltips/_setup_accessibility/_setup_tab_order all exist and are called from library_screen_builder.py:169-171) — accepted, new button wired into all three.
- Finding 6: verified (status_text() unconditionally uses len(state.scanned_records)) — accepted, added a duplicate_count_label showing "N duplicates hidden" when the toggle is on.

## Round 2 — Codex

1. BUG — blank metadata still collapses: _to_display_row() converts None/blank title/artist to the "—" placeholder before rendering, so reading rendered cell text back never sees None — two blank-metadata tracks both render "—"/"—" and would still incorrectly group.
2. BUG — typing into search desyncs dedup: _on_search_changed() calls only _apply_filter() directly (not through render()), so the planned _apply_duplicate_filter() (wired only into render()) wouldn't run on every keystroke, un-hiding previously-suppressed duplicates until the next full render.
3. RISK — group_duplicate_rows's return shape was left "TBD," blocking concrete tests.
4. PROCESS — OpenSpec artifact list named only 4 of the 7 required files, and omitted the verification command sequence.

VERDICT: REVISE

### Claude's response
- Finding 1: verified (library_view_model.py:93-94, `_DASH` placeholder) — accepted. _duplicate_group_key now also treats the literal "—" placeholder string as blank, not just None/empty, since that's the only form the row-level reader ever actually sees.
- Finding 2: verified (library_screen_rendering.py:154-156) — accepted. Introduced a single composite `_apply_search_and_duplicate_filters()` calling _apply_filter() then _apply_duplicate_filter() in order; both render() and _on_search_changed() now call the composite instead of _apply_filter() directly, so the two passes can't run out of sync.
- Finding 3: accepted — locked the contract to `suppressed_duplicate_paths(rows) -> set[str]` (paths to hide), mirroring the existing `_apply_constraint_colors(excluded: frozenset[str], locked: frozenset[str])` pattern already in the same file.
- Finding 4: accepted — PLAN.md now names all 7 openspec artifacts and the full verification command sequence explicitly.

## Round 3 — Codex

1. RISK — artist normalization was left unspecified (only title normalization was detailed), risking case/whitespace variants being treated as different artists.
2. RISK — representative ranking's "fewer missing fields" criterion had no parsing contract against the formatted _RowInfo text (e.g. "bpm, camelot_key" or "—").

VERDICT: REVISE

### Claude's response
- Both accepted, small precise fixes. Added explicit `_normalize_artist_for_grouping(artist) -> str` = `artist.strip().casefold()`, no suffix stripping. Changed `_RowInfo` to carry a pre-computed `missing_field_count: int` (0 for the "—" placeholder, else `len(text.split(", "))`, matching exactly how `_fmt_missing` joins field names in the first place) instead of raw formatted text, so ranking never has to parse display strings.

## Round 4 — Codex

1. BUG — normalization order conflicts with the regex contract: title was lowercased before suffix-stripping, but the suffix regex was written against real-case text ("Energy", uppercase Camelot letters); lowercasing first would silently disable suffix matching without an explicit re.IGNORECASE.

VERDICT: REVISE

### Claude's response
- Accepted, real and simple. Reordered `_normalize_title_for_grouping`: strip suffixes against original-case text first, casefold last (rather than adding re.IGNORECASE, which would have worked too, but reordering is simpler and avoids a second regex-compilation detail to get right).

## Round 5 — Codex

All prior findings confirmed resolved. No new material problems found.

VERDICT: APPROVED

## Resolution
Converged after 5 rounds. Plan approved by Claude (Act 1 grill) and Codex (Act 2 adversarial review, gpt-5.6-sol). Round 1 forced a major architectural correction (dedup moved from the data layer to a row-level pass composed with the existing search mechanism) after Codex traced the real render()/`_apply_filter()` call chain and found the original design would have permanently broken search for suppressed duplicates.

## Act 3 — Build (Claude, direct implementation)

Implemented tasks 4-10 of `openspec/changes/library-hide-duplicate-versions/tasks.md` following the locked `PLAN.md` contracts exactly, strict RED-first TDD throughout.

### Production changes

- `src/xfinaudio/desktop/library_filter.py` — added `_normalize_title_for_grouping` (repeated suffix-stripping loop, original-case-first then casefold-last, per the Round 4 correction), `_normalize_artist_for_grouping` (`artist.strip().casefold()`, per Round 3), `_duplicate_group_key` (None/blank/`"—"` placeholder guard, per Rounds 1-2), `_RowInfo` NamedTuple, `_pick_duplicate_representative` (4-level tiebreak), `suppressed_duplicate_paths` (group-and-suppress, per the Round 2 locked-down return shape).
- `src/xfinaudio/desktop/library_screen_rendering.py` — new `_apply_duplicate_filter()` (row-level, reads rendered `QTableWidgetItem` text for currently-visible rows only, updates `duplicate_count_label`) and composite `_apply_search_and_duplicate_filters()`; `render()` and `_on_search_changed()` rewired to call the composite instead of `_apply_filter()` directly (per the Round 2 desync fix); `_refresh_filter_state`/`clear_quick_filters`/`restore_quick_filters` updated via a new `_all_filter_buttons()` helper to include `hide_duplicates_button`. `LibraryFilters`/`_current_library_filters()` left untouched, confirmed via `git diff`.
- `src/xfinaudio/desktop/library_screen_builder.py` — added `hide_duplicates_button` (checkable, same checked-style stylesheet, deliberately excluded from `quick_filter_buttons`) and `duplicate_count_label`.
- `src/xfinaudio/desktop/screens/library_screen.py` — `hide_duplicates_button.clicked` wired directly to `_refresh_filter_state` (bypassing the mutual-exclusion logic); added to `_setup_button_tooltips()`. Deliberately **not** added to `_setup_accessibility()`/`_setup_tab_order()` — verified by reading both methods first that none of the 5 existing quick-filter buttons appear in either, so the established pattern for those two methods is absence, not presence; matching it exactly. Documented as a clarified interpretation in `apply-progress.md`, not a silent deviation.

### Tests added (RED-first, confirmed failing before each corresponding production change)

- `tests/test_library_filter.py` — 28 new tests (normalization suffix-stripping incl. order-independence and repetition, remix-descriptor preservation, artist case/whitespace, blank/None/placeholder-dash guard, all 4 representative tiebreak levels, `suppressed_duplicate_paths` group semantics).
- `tests/test_library_screen.py` — 14 new tests (`_state_with_duplicates()` fixture; toggle collapses/uncollapses rows; search never un-hides a suppressed duplicate; dedup only considers search-visible rows; toggle independence from both mutual-exclusion groups; Clear Filters and undo-restore coverage; active-count sum; duplicate-count label in all 4 states).

### Verification (all commands from `AGENTS.md:58-63`, in order)

| Command | Result |
|---|---|
| `uv run pytest -q` | PASS — 1059 passed |
| `uv run pyright src tests` | PASS — 0 errors, 0 warnings |
| `uv run pytest --cov --cov-fail-under=70 -q` | PASS — 90.43% coverage |
| `uv run ruff check .` | PASS |
| `uv run ruff format --check .` | PASS — 263 files formatted |
| `uv run python scripts/release_gate_check.py --run` | PASS — full gate, exit code 0 |

`openspec/changes/library-hide-duplicate-versions/tasks.md` tasks 4-10 marked `[x]`; `apply-progress.md` and `verify-report.md` filled in with full TDD-cycle and requirement-by-requirement evidence tables; `state.yaml` updated to `apply: complete`, `verify: complete`, `step: verify`, `next_recommended: review`. Tasks 11 (native review) and 12 (archive) left unchecked for the orchestrator.

## Act 4 — Native review (Claude ↔ gentle-ai review, post-apply gate)

Ran the native `gentle-ai review` lifecycle (4R lens set, high risk tier, 17-18 changed files) per this repo's post-apply governance.

**Lineage 1 — `review-9967994641103116`**: risk and readability found non-blocking issues. Reliability found a **CRITICAL**: `_normalize_title_for_grouping` preserved parenthetical content as an opaque block, so of the three real screenshot titles motivating this whole feature, two had the remix descriptor wrapped in parens and one didn't (a real-world export inconsistency) — they normalized to two different group keys instead of one, so Hide Duplicates silently failed to collapse its own primary use case. Also found: `_DASH` triplicated across 3 modules (readability WARNING), a pluralization bug — "1 duplicates hidden" (readability WARNING), stylesheet/separator duplication (2 readability SUGGESTIONs), a per-keystroke performance concern for the new row-level dedup pass on large libraries with no debounce (resilience WARNING), and a label-ambiguity nit (resilience SUGGESTION). Correctly **escalated** on the CRITICAL.

**Corrections applied**: `_normalize_title_for_grouping` now strips `(`/`)` as punctuation (verified by hand-tracing all three real screenshot titles now normalize identically to `"right on track kwikmix by dj richie rich"`, plus a negative-control test confirming genuinely different remix descriptors like the Billie Jean example still don't group). `_DASH` and a new `MISSING_FIELDS_SEPARATOR` constant now import from their single source (`library_view_model.py`) instead of being redefined. The count label is singular/plural-aware and distinguishes toggle-off (empty) from toggle-on-zero-found ("No duplicates found"). The checked-button stylesheet is a shared constant. The performance WARNING was deliberately left unfixed (proper fix needs new debounce infrastructure beyond this change's scope) — disclosed, not silently dropped.

**Lineage 2 — `review-193e3a2f9299bd42`** (re-review): risk, resilience, readability all confirmed clean (resilience re-flagged the performance item as `pre-existing`/expected, not new). Reliability confirmed the CRITICAL fix by independently hand-tracing the same three titles, and found one new WARNING: the paren-stripping fix has an inherent, narrow false-positive-grouping risk — two genuinely different titles sharing identical words modulo parentheses (e.g. "Track One (B-Side)" vs "Track One B-Side") would now collide into one group. Accepted as a disclosed, non-blocking tradeoff of the CRITICAL fix (display-only, reversible by unchecking, no data loss) rather than engineered away. **Approved.** Receipt: `.git/gentle-ai/review-transactions/v2/review-193e3a2f9299bd42/review-receipt.json`.

Final verification: 1061 tests passed (1059 after Act 3 + 2 more from the native-review corrections), pyright 0 errors, ruff check/format clean.

Status: **Native review approved. Proceeding to archive.**
