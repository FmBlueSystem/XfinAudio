# Design: Strategy UX Clarity and Duplicate Dedupe

## Scope of this document

Architecture-level HOW for the three defects fixed by
`strategy-ux-clarity-and-dedupe`. No task steps here (see `tasks.md`). Additive
semantics only; no strategy scoring, color/energy, or Serato-V2 behavior changes.

## Architectural context (verified against current code)

Layering (lower → higher): `library` → `recommendation` → `application` →
`desktop`. `recommendation/` MUST NOT import `desktop/`. `recommendation` and
`application` already depend on `library` (`library.models.TrackRecord`), so
`library/` is the correct home for any helper shared between the display layer
and the recommendation pool.

Strategy string flow when the DJ clicks Recommend (current code):

1. `BuildScreen._on_recommend` (build_screen.py:404-406) emits
   `recommend_requested(strategy_combo.currentText(), [])`.
2. `MainWindow._on_recommend_requested` → `RecommendationService.on_recommend_requested`
   (recommendation_service.py:221-227): `findText(strategy_name)` → `setCurrentIndex` → `recommend()`.
3. `RecommendationService.recommend` (recommendation_service.py:145) reads
   `strategy_combo.currentText()` and passes it to the worker →
   `workflow_service.recommend(records, strategy_name, ...)`.
4. Downstream resolution is always through `StrategyRegistry.get()/resolve_name()`
   (strategies.py:141-152), which already accepts **both** internal names and
   display labels. `PlaylistStrategy.name` (internal) is what lands in
   `recommendation.strategy.name`, which is what export JSON persists
   (playlist_exporters.py:63). Persistence is therefore internal regardless of
   what the combo emits.

Two combo readers are **already written defensively** as
`currentData() or currentText()`:
- `BuildScreen.render` (build_screen.py:338)
- `PrepCopilot` (prep_copilot.py:65)

This is the decisive signal that the intended design is `itemData(internal_name)`.

Recommendation candidate pool (the path that produced "Too Hot" x2):

- `plan_recommendation_candidates` (application/recommendation_candidates.py:11-27)
  → optionally `prefilter_strategy_candidates` (strategy hard filters over the
  FULL library) → `build_recommendation_pool(..., limit=25)`
  (candidate_pool.py:123, `_DEFAULT_LIMIT = 25`).
- The 25-cap lives inside `build_recommendation_pool`. Control paths
  (locked/manual/start/end) are front-loaded there and must survive.
- `_preserved_control_paths` (playlist_service.py:472-478) already encodes the
  "must survive" set = `locked ∪ manual ∪ start ∪ end − excluded`.

Existing duplicate grouping (display-only, in `desktop/library_filter.py`):
`_normalize_title_for_grouping`, `_normalize_artist_for_grouping`,
`_duplicate_group_key`, `_RowInfo`, `_pick_duplicate_representative`,
`suppressed_duplicate_paths`. These import `_DASH` from
`desktop/library_view_model.py` — a real coupling that must be broken to reuse
the core in `recommendation/`.

## Decision 1 — Strategy-description refresh mechanism (Item 1)

**Decision.** Add an internal slot `BuildScreen._on_strategy_changed` connected in
`BuildScreen._connect_signals` to `strategy_combo.currentIndexChanged`. Store the
ViewModel on `render` (mirroring the established `LibraryScreenRenderingMixin`
pattern of `self._last_vm`) and have the slot set the label from the same code
path `render` already uses.

- **Signal: `currentIndexChanged`, not `currentTextChanged`.** Selection is
  data-backed after Decision 2 (`itemData(internal_name)`); the canonical
  "selection changed" for a data-backed combo is the index change. It reads the
  selected item's data, not its visible text.
- **Connection lives inside `build_screen`**, not MainWindow wiring. Consistent
  with existing internal slots (`_on_spectral_cohesion_changed`,
  `_on_apply_variant`). No new cross-object signal needed.
- **No double-set conflict with `render():339`.** The slot and `render` both set
  `strategy_explanation_label` from `vm.strategy_explanation(currentData())`,
  which flows through `describe_strategy → default_strategy_registry().get()`.
  Because both derive from the identical `(current selection, same registry
  description)`, the strings are byte-identical; whichever fires last writes the
  same text. `render` populates the combo (build_screen.py:305-307) and stores
  the vm; the slot only fires on later user interaction, so the vm is always
  present by then. Guard `if self._last_vm is not None` covers the pre-render
  edge.
- **Display-label resolution verified.** `describe_strategy` calls
  `registry.get(name)`, and `get` → `resolve_name` accepts display labels, so the
  label refresh works whether the slot passes `currentData()` (internal name) or
  a display label. With Decision 2 it passes the internal name via `currentData()`.

**Rejected.** `currentTextChanged` (couples the refresh to visible text rather
than the selected item's data key). MainWindow-side wiring (unnecessary
indirection; the widget already owns its other slots). Re-deriving the
description from a locally cached `dict[str,str]` instead of the vm (introduces a
second description source that can drift from `render`).

## Decision 2 — Display names in the combo (Item 2)

**Decision.** Populate the combo with `addItem(display_name, internal_name)`
(text = `option.display_name`, data = `option.name`) and read the internal name
via `currentData()` at the two remaining raw `currentText()` sites. Keep the
emitted/flowing value byte-identical to today (the internal name), so the entire
recommendation/persistence/export chain is untouched. `resolve_name` remains as
defense-in-depth, not load-bearing on every call.

Concrete edits (4 sites):
1. build_screen.py:307 — `addItem(option.name)` → `addItem(option.display_name, option.name)`.
2. build_screen.py:405 (`_on_recommend`) — `currentText()` → `currentData()`.
3. recommendation_service.py:145 (`recommend`) — `currentText()` → `currentData()`.
4. recommendation_service.py:224 (`on_recommend_requested`) — `findText(strategy_name)`
   → `findData(strategy_name)` (the param now carries an internal name emitted by
   `currentData()`; the combo text is now the display label, so `findText` would fail).

No change needed at build_screen.py:338 or prep_copilot.py:65 — both already read
`currentData() or currentText()` and will now resolve `currentData()` to the
internal name.

**Consumer audit (all confirmed safe because emission stays internal):**
- Recommendation worker / `workflow_service.recommend` — receives internal name,
  as today. No change.
- `prefilter_strategy_candidates` (playlist_service.py:385) — `registry.get(str(name))`
  first, then compares the RESOLVED `strategy.name` against `_COLOR_FILTER_STRATEGIES`.
  Never compares the raw input to internal literals.
- `plan_recommendation_candidates(strategy_name=...)` — passes through to prefilter.
- Prep Copilot (`prep_copilot.py:65`) — already `currentData() or currentText()`.
- Saved-playlist export / export naming / export JSON — persists
  `recommendation.strategy.name` (internal `PlaylistStrategy.name`), unaffected by combo text.

**Why this over "display-name emission end-to-end" (Approach A: change only
`addItem`).** Approach A touches one line but changes the *semantic content* of
the string flowing through every backend layer, making `resolve_name` load-bearing
on every hop and risking any future raw `== "internal_name"` comparison. Approach B
touches ~4 desktop lines but keeps the backend contract byte-identical (emitted
value = internal name, before and after) — the smallest *consistent* blast radius,
and it matches the two already-defensive `currentData()` readers. Persisted
artifacts stay internal in both approaches; B is strictly safer.

**Rejected.** Approach A (display-name emission end-to-end).

## Decision 3 — Duplicate dedupe in the recommendation pool + layering (Item 3)

### 3a. Relocate the pure grouping core to a layer-safe module

**Decision.** Create `src/xfinaudio/library/duplicate_grouping.py` holding the
Qt-free, TrackRecord-agnostic core:

- `normalize_title_for_grouping(title: str) -> str`
- `normalize_artist_for_grouping(artist: str) -> str`
- `duplicate_group_key(title, artist, *, placeholder: str | None = None) -> tuple[str, str] | None`
  — the `_DASH` check becomes a parameter (`placeholder`); desktop passes `_DASH`,
  recommendation passes `None`. This removes the `desktop.library_view_model`
  dependency from the core.
- `duplicate_representative_sort_key(*, is_complete: bool, missing_field_count: int,
  title: str, path: str) -> tuple[int, int, int, str]` — the exact ordering used
  today: `(0 if complete else 1, missing_field_count, len(title), path)`.

`desktop/library_filter.py` re-imports these and keeps `_RowInfo`,
`_pick_duplicate_representative`, and `suppressed_duplicate_paths` as thin
delegators — **imports only, no logic change**, so the Library screen display
filter stays byte-identical. `_duplicate_group_key` in desktop passes
`placeholder=_DASH`; `_pick_duplicate_representative` builds the sort key via the
neutral helper.

`library/` is a lower layer than `recommendation/`, so
`recommendation` importing `library.duplicate_grouping` respects the boundary
(no `recommendation → desktop` import). Verified: `recommendation` already
imports `library.models`.

**Rejected.** Moving the whole `library_filter` module (drags Qt-adjacent
`_RowInfo`/rendered-row concepts into `library`). Duplicating the normalization
regexes in `recommendation` (two sources of truth that will drift; the whole
point is byte-identical grouping semantics).

### 3b. Record-level dedupe function

**Decision.** Add `dedupe_recommendation_duplicates(records: list[TrackRecord],
controls: DJControls | None) -> list[TrackRecord]` in
`src/xfinaudio/recommendation/candidate_pool.py` (co-located with
`build_recommendation_pool`, which already computes the control-priority set).

Algorithm (order-preserving, deterministic):

```
preserve = manual ∪ start ∪ end ∪ locked   (− excluded)   # same set as _preserved_control_paths
groups: dict[key, list[TrackRecord]] keyed by
        duplicate_group_key(r.title, r.artist, placeholder=None)   # None key ⇒ singleton
suppressed: set[str] = {}
for group with len >= 2:
    controls_in_group = [r for r in group if r.path in preserve]
    if controls_in_group:
        keep = controls_in_group        # every control survives; non-controls suppressed
    else:
        keep = [min(group, key=duplicate_representative_sort_key-of-record)]
    suppress every group member whose path not in {k.path for k in keep}
return [r for r in records if r.path not in suppressed]   # original order preserved
```

Record adapter for the representative key: `is_complete = r.metadata_status ==
"complete"`, `missing_field_count = len(r.missing_required_fields)`,
`title = r.title or ""`, `path = r.path`. This reproduces the display-side
representative ordering (complete first, fewer missing fields, shorter title,
path tiebreak).

Control immunity is twofold: control paths are never added to `suppressed`, and
when a group contains a control the control(s) are the survivors (non-control
duplicates drop out). Records with `None`/blank/placeholder title or artist never
group (key `None`), so incomplete-metadata tracks are never falsely collapsed.

**Preserve-set sourcing.** `candidate_pool.build_recommendation_pool` already
builds the control-priority list inline; the dedupe function reuses the same
composition locally. To avoid a fourth private copy of that set logic, the design
permits promoting `_preserved_control_paths` from `playlist_service.py` to a
public `preserved_control_paths` in `recommendation/controls.py` (its natural
home, beside `DJControls`/`apply_controls`) and calling it from both
`playlist_service` and `candidate_pool`. This is optional cleanup; the fallback
is an inline 4-line set build in the dedupe function. Either keeps the pool PR
self-contained.

### 3b SUPERSEDED (2026-07-20) — Stricter Playlist-Level Grouping Key

The original Decision 3b's algorithm specification (line 182) called for
`duplicate_group_key(r.title, r.artist, placeholder=None)` as the grouping key
for `dedupe_recommendation_duplicates`. This was the conservative key, identical
to the Library display filter's semantics—keeping distinct parenthetical
descriptors (e.g., "(Clean)" vs "(Single Version)") as separate groups.

**Maintainer decision (2026-07-20): SUPERSEDED.** The recommendation pool now
uses a stricter, playlist-level key: `playlist_duplicate_group_key`, implemented
via `normalize_title_for_playlist_grouping`, which **ignores parenthetical
descriptor content entirely**. This aggressive grouping collapses "(Clean)",
"(Single Version)", and the base title to a single group for candidate-pool
deduplication purposes. Concretely: "Too Hot (Clean)", "Too Hot (Single Version)",
and "Too Hot" all normalize to the same playlist group key, so only one
representative survives in the pool.

**Library filter unchanged.** The Library display screen's duplicate grouping
retains the conservative key semantics (via `duplicate_group_key` with
`placeholder=_DASH`), keeping distinct variants visually separate to the DJ.
No changes to `desktop/library_filter.py` beyond the existing delegation pattern.

**Implementation references:**
- `src/xfinaudio/library/duplicate_grouping.py`: `normalize_title_for_playlist_grouping` (new) and `playlist_duplicate_group_key` (new)
- `src/xfinaudio/recommendation/candidate_pool.py`: `dedupe_recommendation_duplicates` uses `playlist_duplicate_group_key` instead of `duplicate_group_key(..., placeholder=None)`
- `src/xfinaudio/desktop/library_filter.py`: unchanged; still delegates to conservative key

### 3c. Placement relative to the 25-cap

**Decision.** Call the dedupe in `plan_recommendation_candidates`
(application/recommendation_candidates.py) on `pool_source` AFTER
`prefilter_strategy_candidates` and BEFORE `build_recommendation_pool`, for both
the strategy and no-strategy branches:

```
pool_source = scanned_records
if strategy_name is not None:
    pool_source = prefilter_strategy_candidates(scanned_records, strategy_name, controls)
pool_source = dedupe_recommendation_duplicates(pool_source, controls)   # NEW, before the cap
return build_recommendation_pool(pool_source, controls, limit)
```

This guarantees the 25 slots are spent on distinct versions rather than
duplicates, and the recommendation built from that pool is duplicate-free.
`build_recommendation_pool` still front-loads control tracks, so anchors survive
the cap unchanged.

**Rejected.** Placing dedupe inside `prefilter_strategy_candidates` — it has 10
callers (including `library_controller`), so it would change behavior far beyond
the interactive recommendation pool. `plan_recommendation_candidates` is the
narrow, correct seam for the interactive path that exhibited the defect.

## Data model impact

None. No schema, `AppState`, `PlaylistStrategy`, `TrackRecord`, or export-format
changes. `strategy_combo` gains item data (Qt widget state only). Persisted
strategy names remain internal.

## Regression surface & safety

- **Duplicate-free libraries: byte-identical.** When no group has ≥2 members,
  `dedupe_recommendation_duplicates` suppresses nothing and returns the input
  list in original order → `build_recommendation_pool` sees the same input as
  today. Locked in by a characterization test.
- **Library screen display filter: unchanged.** 3a is imports-only for
  `library_filter.py`; `suppressed_duplicate_paths`/`_RowInfo` logic is untouched.
  Existing `tests/test_library_filter.py` must stay green with no edits.
- **Control/anchor immunity.** Controls never suppressed; a group with a control
  keeps the control. Covered by an anchor-in-duplicate-group test.
- **No audio mutation, no DSP, no Serato-V2 writes.** Pure in-memory list
  transforms and a Qt combo/label change.

## Test plan (strict TDD, RED → GREEN → REFACTOR)

Item 1 — label refresh:
- Qt offscreen: after `render`, change `strategy_combo` selection
  (`setCurrentIndex`) and assert `strategy_explanation_label.text()` equals the
  newly selected strategy's description immediately (no re-render).

Item 2 — display names + resolution:
- Combo item text = `display_name`, item data = internal name, for every strategy.
- `_on_recommend` emits the internal name via `currentData()`; end-to-end the
  recommendation resolves to the correct `PlaylistStrategy` and export JSON
  `strategy` stays internal (`same_color_energy`, not "Same Color & Energy").
- `on_recommend_requested` selects the right item via `findData`.

Item 3 — pool dedupe:
- "Too Hot" x2 fixture in the pool → exactly one representative survives; the
  representative is the complete / fewer-missing / shorter-title / path-tiebreak
  choice.
- Control-path immunity: a duplicate group whose member is the anchor
  (start/locked/manual) always keeps the control.
- No-duplicates characterization: pool output byte-identical to pre-change.
- Helper-relocation regression: `library_filter` display behavior unchanged
  (existing `test_library_filter.py` green, no edits).

## Line-budget forecast & delivery split (honest flag)

The three items plus their tests will **exceed the 400-line review budget**,
driven mainly by Item 3 (new `library/duplicate_grouping.py`, the
`library_filter` delegation refactor, the record-level dedupe, and its tests).

**Recommended chained-PR split** (matches the proposal's natural boundary):
- **PR1 — UI (Items 1 + 2):** `build_screen.py`, `recommendation_service.py` +
  Qt/offscreen tests. Estimated well under 400 changed lines.
- **PR2 — Pool (Item 3):** `library/duplicate_grouping.py`,
  `desktop/library_filter.py` (imports-only), `recommendation/candidate_pool.py`,
  `application/recommendation_candidates.py`, optional
  `recommendation/controls.py` promotion + tests. Sized to stay under 400 on its
  own.

Each PR is independently revertible and additive; PR1 and PR2 have no ordering
dependency (UISlot vs pool seam are disjoint).

## Affected files (design-level)

| File | Change | Item |
|------|--------|------|
| `src/xfinaudio/desktop/screens/build_screen.py` | `_on_strategy_changed` slot + `currentIndexChanged` wiring; store `_last_vm`; `addItem(display_name, internal_name)`; `_on_recommend` → `currentData()` | 1, 2 |
| `src/xfinaudio/desktop/recommendation_service.py` | `recommend` → `currentData()`; `on_recommend_requested` → `findData` | 2 |
| `src/xfinaudio/library/duplicate_grouping.py` | NEW: neutral normalization + group-key (parametrized placeholder) + representative sort-key | 3 |
| `src/xfinaudio/desktop/library_filter.py` | Delegate to `library.duplicate_grouping` (imports only, no logic change) | 3 |
| `src/xfinaudio/recommendation/candidate_pool.py` | NEW `dedupe_recommendation_duplicates(records, controls)` | 3 |
| `src/xfinaudio/application/recommendation_candidates.py` | Call dedupe before `build_recommendation_pool` | 3 |
| `src/xfinaudio/recommendation/controls.py` | (Optional) promote `preserved_control_paths` for reuse | 3 |
| `tests/` | RED tests per item | 1, 2, 3 |

## Open decisions requiring validation in tasks/apply

- Whether to promote `_preserved_control_paths` to `recommendation/controls.py`
  (DRY) or inline the 4-line set in the dedupe function (self-contained pool PR).
  Default: promote if it stays within PR2's budget; otherwise inline.
