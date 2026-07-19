# Proposal: Serato Export Partial-Success Semantics

## Intent

A successful Serato crate write can currently become an unrecorded partial
operation. When the crate is already on disk and readiness-sidecar generation
fails with any exception other than `OSError`, that exception escapes before the
UI is updated, before export history is recorded, and before the success
callback decision is made. The user is left with a real crate in Serato but no
guidance label, no status text, no history receipt, and an ambiguous UI state —
the app looks like the export failed even though the crate succeeded.

This change makes partial success an explicit, tested outcome so a crate that
reached disk is always reported and recorded, regardless of how sidecar
generation fails. It also removes two readability liabilities in the export
dependency bundle that make the export boundary harder to reason about and
review. It addresses exactly the three deferred findings from
`docs/reviews/REVIEW-DIFF-2026-07-18-terminal-findings.md` (`RES-002`,
`READ-005`, `READ-006`) and nothing more.

Success looks like: a non-`OSError` sidecar failure after a successful crate
write behaves identically to the already-handled `OSError` case — crate path
reported, sidecar failure surfaced, history receipt persisted, callback policy
explicit and covered by tests — and the export dependency bundle exposes only
consumed collaborators with statically checked contracts.

## Proposal Question Round

Interactive questions were skipped: the scope is fully pre-decided by the
terminal findings document, which fixes the five required observable outcomes
for `RES-002` and the required remediation for `READ-005` and `READ-006`.

Assumptions carried into spec/design:
- Preserve all existing product behavior; only the failure boundary changes.
- The non-`OSError` path must converge on the exact behavior already
  implemented for the `OSError` branch (report failure, record receipt with
  `readiness_json_path=None`, suppress callback), so partial-success handling is
  uniform across failure types rather than special-cased per exception.
- No new user-facing feature, no audio mutation, no DSP, no live Serato V2
  writes; the crate-write path is unchanged and must never be re-entered by a
  sidecar retry.

## Scope

### In Scope
- Broaden the readiness-sidecar failure boundary in
  `serato_recommendation_export.py` so a non-`OSError` failure after a successful
  crate write degrades gracefully instead of escaping, matching the existing
  `OSError` behavior.
- Guarantee the crate write stays successful when only sidecar generation fails,
  and that a sidecar retry never rewrites or corrupts the already-written crate.
- Surface both the successful crate path and the sidecar failure in the export
  guidance label and status text.
- Record the partial-success receipt in export history via `_record_serato_export`
  with the crate path present and the readiness JSON path absent.
- Make the success-callback policy on partial success explicit and test-covered
  (recommended: suppress the callback on any sidecar failure, for consistency
  with the current `OSError` behavior; the design phase settles this).
- `READ-005`: remove `write_application_dj_readiness_report` from
  `ExportDependencies` (it is unused via the bundle — `serato_recommendation_export.py`
  uses `dependencies.write_readiness_sidecars` and `export_actions.py:55` imports
  the function directly), or route the intended behavior through the bundle.
- `READ-006`: replace the seven `Callable[..., Any]` collaborator fields in
  `ExportDependencies` with explicit protocols or typed aliases per collaborator
  shape.

### Out of Scope
- New export features, UI/UX redesign, or changes to the crate-writing logic
  itself.
- Audio mutation, DSP, real-time analysis, or live Serato database V2 writes.
- Changes to readiness-report content, sidecar file format, or export-history
  schema beyond recording the existing partial-success fields.
- Any finding not listed in the terminal findings document.

## Capabilities

### New Capabilities
- None. This is a resilience and readability remediation of existing behavior.

### Modified Capabilities
- `serato-recommendation-export`: partial-success is now an explicit, uniform
  outcome across all sidecar-failure types, and the export dependency bundle
  exposes only consumed collaborators with statically checked contracts.

## Approach

Use strict RED → GREEN → REFACTOR → VERIFY.

1. `RES-002`: write a RED test that raises a non-`OSError` exception from
   `write_readiness_sidecars` after a successful crate write and asserts the five
   required outcomes (crate reported, failure surfaced, history recorded,
   callback policy honored, crate untouched by any retry). Then widen the
   `except` boundary minimally so the non-`OSError` path reuses the existing
   graceful-degradation logic. Keep the `OSError` and non-`OSError` handling
   convergent rather than duplicated.
2. `READ-005`: confirm the collaborator has no bundle consumer, then remove it
   from `ExportDependencies` and `default_export_dependencies`, leaving the
   direct import in `export_actions.py` intact.
3. `READ-006`: introduce explicit `Protocol`/typed-alias contracts for each of
   the remaining collaborators and apply them to the dataclass fields, verified
   by `pyright`.

Deliver within the 400-line review budget as a single slice if it fits;
otherwise auto-chain via the feature-branch-chain strategy (`RES-002` first,
then the `READ-005`/`READ-006` readability slice).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/xfinaudio/desktop/serato_recommendation_export.py` | Modified | Broaden sidecar-failure boundary to non-`OSError`; uniform partial-success |
| `src/xfinaudio/desktop/export_dependencies.py` | Modified | Remove unused collaborator; replace `Callable[..., Any]` with typed contracts |
| `tests/` (Serato export) | Modified | RED test for non-`OSError` partial success; callback-policy coverage |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Broadening `except` masks a genuinely fatal error and hides a real defect | Medium | Log with `LOGGER.exception`; only degrade the sidecar step, never the crate write; assert logging in tests |
| Sidecar retry re-enters or corrupts the crate write | Low | Spec/tests forbid crate rewrite on retry; crate path is written once before the sidecar step |
| Callback-policy change alters downstream export-flow expectations | Medium | Make policy explicit in spec, keep it consistent with existing `OSError` behavior, cover with tests |
| Removing a bundle collaborator breaks a hidden consumer | Low | Verify no bundle consumer exists before removal; `pyright` and full suite guard against regressions |
| Typed-contract migration changes runtime behavior | Low | Types are static-only; behavior asserted unchanged by existing tests |

## Rollback Plan

Revert each slice independently. The crate-write path is unchanged, so reverting
restores the prior failure boundary and the prior dependency-bundle shape without
touching persisted user data, crates, or export history.

## Dependencies

- Existing `uv`, pytest, Pyright, Ruff, and release gate.
- No new runtime dependencies.

## Success Criteria

- [ ] A non-`OSError` sidecar failure after a successful crate write no longer
      escapes; the crate write remains successful.
- [ ] Partial success is visible in both the export guidance label and status
      text (crate path plus sidecar failure).
- [ ] Export history records the partial-success receipt (crate path present,
      readiness JSON path absent).
- [ ] The success-callback policy on partial success is explicit and covered by
      tests.
- [ ] Retrying sidecar generation never rewrites or corrupts the crate.
- [ ] `ExportDependencies` exposes only consumed collaborators, each with an
      explicit, `pyright`-checked contract (no `Callable[..., Any]`).
- [ ] Full verification and the release gate pass.
