# Feature: XfinAudio 2.0 — scientific foundation (harmonic core v2 + engine pack)

## Goal

Deliver version 2.0.0: a science-informed engine upgrade. Authorized autonomously
by the user ("vamos por la ciencia, actua en forma autonoma hasta tener la nueva
version"). Major bump justified: scoring semantics change.

## Scope (the 2.0 definition)

1. Harmonic core v2: continuous tonal compatibility (Tonal Interval Vectors,
   audio-derived via librosa chroma — same precomputation infrastructure as the
   spectral profiles) entering scoring as an additional weight; Camelot gates
   deprecate gradually to an explanation/UI layer. Basis: Gebhardt/Davies/Seeber
   2015 (signal-level consonance beats circle-of-fifths systems), Bibbo/Faraldo
   2022 (TIV + pitch-shift, 73.7% improvement), key-tag noise literature.
   User's ear is the final listening test (A/B same intent, both modes).
2. Engine pack (community + science reinforced): T1 triads/tandas (cluster
   scoring window of 3 + rehearsed-together provenance flag), T3 runtime
   budgeting (target_minutes on DJControls/prep intent; duration exists),
   T4 slot-role programming (warmup/peak/closing arc curves), T9 contingency
   branches (start_path/locked_paths already exist).
3. Carry-over: MIK slice C (metadata screen UI + safe-folder gap export).

## Routes (dependency order)

1. MIK slice C on feat/ai-set-narrative (closes the open feature).
2. Harmonic core v2 explore (audio pipeline + scoring/optimizer signatures)
   -> TIV precomputation spike -> dual-scoring integration -> A/B harness.
3. Engine pack T1/T3/T4 on the foundation outcome (Camelot tricks are
   re-expressed AFTER the harmonic core decision, not before).
4. Release cut (version bump, DMG, tag) = USER decision at the end.

## Constraints

- Existing scoring behavior is pinned by tests: characterization first, then
  change. No silent gate removal — dual scoring until A/B validates.
- Strict TDD, offline tests (fake transport/injected analysis), coverage floor 89,
  render-contract anchors untouched, AGENTS.md 400-line review budget per slice.
- Per-track TIV is a PRECOMPUTATION stored like the spectral profiles, not an
  on-the-fly analysis.
- Every slice closes with work-unit commits + independent orchestrator
  verification, as in all prior slices.

## Evidence

- Harmonic core v2 spike: commit 6f105f2 (TIV precomputation chroma->6-dim
  fold, tiv_compatibility cosine, schema v6 storage parity, scoring tonal
  weight default 0.0 joining COMPATIBILITY axis, scripts/tiv_ab_benchmark.py
  dual-arm harness). 53 new tests; full suite 2386; pinned totals byte-identical.
- Engine pack slice 1 (T3 target_minutes + T4 slot_role): in flight (writer).
- Engine pack slice 2 (T1 triads + provenance tags): pending.
- T9 contingency branches: deferred to a follow-up slice (medium value,
  sequential per-branch runs feasible; not blocking 2.0).
