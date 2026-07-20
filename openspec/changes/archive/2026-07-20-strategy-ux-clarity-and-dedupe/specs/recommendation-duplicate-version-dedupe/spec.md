# Recommendation Candidate Duplicate-Version Dedupe Specification

## Purpose

Define the observable behavior of duplicate-version suppression in the
recommendation candidate pool. The pool MUST keep at most one
representative per near-duplicate group, using the same grouping
semantics as the existing library duplicate-hiding filter, while never
removing a control track and never changing output for libraries with
no duplicates.

## Requirements

### Requirement: Candidate Pool Keeps One Representative per Group

The recommendation candidate pool MUST include at most one
representative track per near-duplicate group. For the candidate pool,
a group is defined by a playlist-level key that is STRICTER than the
library display filter's key: in addition to stripping app-generated
technical suffixes, it MUST ignore parenthetical descriptor content
entirely (maintainer decision 2026-07-20: "Too Hot (Clean)" and "Too
Hot (Single Version)" are the same song for playlist purposes). The
library display filter's grouping semantics MUST remain unchanged.

#### Scenario: Duplicate versions collapse to one representative

- GIVEN a candidate pool containing multiple near-duplicate versions of
  the same title+artist (differing by app-generated suffixes such as
  `" - 12A - Energy 7"` or `"(v2)"`, or by parenthetical descriptor
  variants such as `"(Clean)"` vs `"(Single Version)"` vs no
  descriptor)
- WHEN the recommendation candidate pool is built
- THEN the pool MUST contain at most one track from that duplicate group

#### Scenario: Live-observed regression is fixed

- GIVEN a candidate pool containing the three live-observed pairs:
  "Too Hot (Single Version)" + "Too Hot (Clean)", "Se La" +
  "Se La (12\" Version)", and "Still" + "Still - 3B - Energy 3"
  (same artists)
- WHEN a recommendation is generated from that pool
- THEN the resulting recommendation MUST contain at most one version of
  each of the three songs

#### Scenario: Library display grouping is unchanged

- GIVEN the Library screen's hide-duplicates toggle
- WHEN titles differ only by parenthetical descriptor content (e.g.
  "(Clean)" vs "(Single Version)")
- THEN the Library display filter MUST keep treating them as distinct
  versions, byte-identical to current behavior

### Requirement: Control Tracks Are Never Removed by Dedupe

Anchor/start, locked, end, and manual-order control tracks MUST never be
removed from the candidate pool by duplicate-version dedupe, even when
they belong to a duplicate group with other candidates.

#### Scenario: A locked duplicate survives dedupe

- GIVEN a candidate pool where a locked track is part of a duplicate
  group with a non-control track
- WHEN duplicate-version dedupe runs
- THEN the locked track MUST remain in the pool
- AND the non-control duplicate(s) in the same group MAY be removed

#### Scenario: Anchor/start, end, and manual tracks survive dedupe

- GIVEN a candidate pool where the anchor/start track, the end track, or
  a manual-order track belongs to a duplicate group with other
  candidates
- WHEN duplicate-version dedupe runs
- THEN that control track MUST remain in the pool regardless of its
  position in the duplicate group

### Requirement: Duplicate-Free Libraries Are Unchanged

When no candidate group has more than one member, duplicate-version
dedupe MUST produce byte-identical recommendation output to the
pre-change behavior.

#### Scenario: No duplicates means no change

- GIVEN a candidate pool where every title+artist grouping key is unique
- WHEN a recommendation is generated before and after this change
- THEN the ordered candidate list, transition scores, and warnings MUST
  be identical

### Requirement: Representative Choice Is Deterministic

Given the same duplicate group, the dedupe step MUST always choose the
same representative track across repeated runs.

#### Scenario: Repeated runs choose the same representative

- GIVEN a fixed duplicate group with the same track metadata
- WHEN the candidate pool is deduped twice in separate runs
- THEN the same representative track MUST be chosen both times

### Requirement: Strategy Filtering Semantics Are Unaffected

Introducing candidate-pool dedupe MUST NOT change the observable
filtering or scoring behavior of `same_color`, `same_energy`, or
`same_color_energy` for any pool that has no duplicate groups, and MUST
NOT alter how the color/energy anchor filters are applied to the
surviving representatives.

#### Scenario: Filtering output is unchanged for duplicate-free pools

- GIVEN a fixed pool of tracks and anchor with no duplicate groups
- WHEN recommendations are generated under `same_color`, `same_energy`,
  or `same_color_energy` before and after this change
- THEN the ordered candidate list and any warnings MUST be identical

#### Scenario: Anchor/energy filters apply to deduped representatives

- GIVEN a pool with a duplicate group where dedupe removes a non-control
  candidate
- WHEN recommendations are generated under `same_color_energy`
- THEN the surviving representative MUST still be subject to the same
  color and energy filtering as any other non-control candidate
