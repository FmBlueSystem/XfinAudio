# Terminal Review Findings Requiring Follow-Up

The `project-audit-remediation` review completed three native 4R rounds and the maximum two correction rounds. The change is locally verified, but one resilience risk and two readability improvements remain. They must be handled in a separate SDD change or explicitly waived by the owner; silently extending the current correction loop would violate the bounded-review policy.

## Decision needed

Create a separate SDD change to address the remaining export-boundary findings. Do not reopen the current correction loop.

## Remaining findings

| ID | Severity | Location | Finding | Required outcome |
|---|---|---|---|---|
| `RES-002` | Warning / risk | `src/xfinaudio/desktop/serato_recommendation_export.py` | After a Serato crate is written, a non-`OSError` readiness-sidecar failure can escape before visible completion, history persistence, and the success callback. This can leave a successful crate write as an unrecorded partial operation. | Define and test explicit partial-success semantics. Record the crate result, surface the sidecar failure, and decide whether the callback runs. |
| `READ-005` | Suggestion | `src/xfinaudio/desktop/export_dependencies.py` | `write_application_dj_readiness_report` remains in the dependency bundle but is not consumed. | Remove the unused collaborator or route the intended behavior through it. |
| `READ-006` | Suggestion | `src/xfinaudio/desktop/export_dependencies.py` | Seven distinct collaborators are typed as `Callable[..., Any]`, hiding their argument and return contracts. | Replace opaque callables with explicit protocols or typed aliases for each collaborator shape. |

## Required behavior for `RES-002`

The follow-up specification must decide these observable outcomes:

1. The crate write remains successful when only sidecar generation fails.
2. The UI reports both the successful crate path and the sidecar failure.
3. Export history records the partial-success receipt.
4. The success callback policy is explicit and covered by tests.
5. Retrying sidecar generation never rewrites or corrupts the crate.

## Verification checklist

- [ ] RED test covers a non-`OSError` sidecar failure after a successful crate write.
- [ ] Partial success is visible in status and export guidance.
- [ ] Export history persists the crate result and sidecar failure.
- [ ] Callback behavior is specified and tested.
- [ ] Dependency collaborators have explicit, statically checked contracts.
- [ ] Focused Serato export tests pass.
- [ ] Full XfinAudio verification and release gate pass.
- [ ] A fresh native review receipt covers the final candidate bytes.

## Review trail

- Initial independent trail: `docs/reviews/REVIEW-DIFF-2026-07-18-r4.md`
- Native lineages:
  - `review-09881e38571158d0`
  - `review-c70450f6282bf40e`
  - `review-f11c8f261adbe74a`
- Terminal native receipt: `.git/gentle-ai/review-transactions/v2/review-f11c8f261adbe74a/review-receipt.json`

## Archive note

This document records follow-up scope; it is not an archive waiver or a substitute for `gentle-ai.verify-result/v1`, `reviewGate.result: allow`, the frozen ledger, or the content-bound terminal receipt required by the SDD archive gate.
