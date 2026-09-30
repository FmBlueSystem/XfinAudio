# 2026-09-30 audit remediation matrix

Scope: shared application correctness/security, Serato export workflows, musical algorithm contracts, and measured incremental reliability/performance improvements. Other DJ exporters are preserved but their specific enhancements are excluded by owner request. Changes remain local; no push, pull request, release or deployment is authorized.

Status vocabulary: **Implemented** = regression-tested focused slice, still subject to the final integrated gate; **In progress** = planned/being implemented; **Accepted** = intentional product behavior; **Excluded** = owner-scoped out; **Blocked validation** = requires unavailable native/external environment, not an untested claim of success.

| Audit finding | Status | Change / evidence |
|---|---|---|
| S1 credential-bearing HTTP/redirects | Implemented | HTTPS-only final endpoints, all redirects rejected, non-forwardable Authorization; offline transport matrix |
| S2 formula-like metadata in CSV | Implemented | Shared literal text encoding for playlist, metadata checklist and readiness CSV; raw JSON/numeric fields unchanged |
| S3 non-Serato filename containment | Excluded | Owner explicitly limited export improvements to Serato; other exporters untouched |
| Loudness overwrites comments automatically | Accepted + disclosure fixed | Normal default-enabled combined analysis/write-back preserved; truthful English/Spanish docs; corrupt-settings recovery alone pauses writes |
| Local DMG build can skip exact-source gate | In progress | Planned fail-closed clean-SHA full gate + bundle provenance/reuse validation |
| GitHub Actions version tags mutable | In progress | Official immutable action commit pins planned |
| FFmpeg signature fetched but unused | In progress | Pinned content SHA remains authoritative; misleading unused signature flow being corrected |
| CQ1 close during active work aborts | Implemented | Asynchronous owned-thread drain; ten subprocess scenarios; no forced terminate |
| CQ2 settings truncation/unrecoverable startup | Implemented | Temporary fsync + atomic replacement, preserved invalid bytes + visible recovery, typed UI failures, recovery-only write-back pause |
| CQ3 stale rescan dirty state | Implemented | Publish cleared state through shell owner; integration assertion |
| CQ4 orphan playlist references | Implemented | FK enforcement per connection + idempotent orphan migration preserving valid order |
| CQ5 connection lifetime depends on GC | Implemented | Transaction context closes explicitly; 100 reads with GC disabled add zero descriptors |
| CQ6 quadratic completion/UI-row work | In progress | Synthetic baseline, immutable tick batching + indexed row lookup planned |
| CQ7 weak mutable/type state contract | In progress | Frozen field snapshots, checked replacement, published scan/render/shell changes and narrow typed ports planned |
| Runtime source/wheel translations/icons missing | Implemented | Shared runtime resolver, icons/QM included in wheel; extracted wheel loads real catalog |
| Linux vanished-folder watcher failure | Implemented | Recoverable watcher warning; fixture directory created; scan completion still finishes |
| Linux narrow Color-column failure | Implemented | Compact Library layout/columns; focused original regression passes |
| F1 generated Apply action hidden | Implemented | Visibility every render, default balanced selection, explicit track-count CTA |
| F2 1000x700 window impossible | Implemented | Generated/applied workflow measured exactly 1000x700; short-display control scrolling and wider prompt |
| F3 inconsistent anchor eligibility | Implemented | Shared complete-anchor eligibility and direct starting-track/repair navigation; AI no-anchor route remains valid |
| F4 fractional BPM truncated | Implemented | Shared precision-preserving display across Library/Review/metadata |
| F5 destination/next-step clarity | In progress / partly Excluded | Serato unset-folder guidance planned; other-software destination text explicitly excluded |
| F6 missing-data worklist buries repairs | Implemented | Incomplete default, human labels, repair checklist + refresh; independent Library filters; one Serato worklist dispatch per click |
| F7 synchronous Prep/no visible generation cancel | In progress | Safe worker-based Prep generation and explicit cancellation/discard semantics planned |
| F8 tooltip-only explanations | Partly implemented | Build keyboard-visible count/pool details done; Review selection details planned |
| Folded BPM reachability drops valid edges | Implemented | Interval-neighbor graph traversal matches independent all-pairs oracle on 20,000 synthetic corpora |
| Count cap drops locked/end controls | Implemented | Mandatory controls preserved before sequencing; infeasible caps diagnosed |
| Duration round-down silently underfills | Implemented | Actual per-track duration coverage and explicit shortage/unknown-duration diagnostics |
| Prep prefix trimming drops end/locks | Implemented | Count applied before sequencing; exclusions before candidate cap; counts above 25 supported |
| Invalid zero/negative/nonfinite BPM accepted | Implemented | Finite-positive parse/fallback contract, defensive legacy scoring and readiness blocking |
| Camelot diagonal direction/explanation wrong | Implemented | Primary-source directional rule, full 24-key truth table, semitone vs whole-step lift descriptions |
| Replacement/backfill can restore excluded tracks | In progress | Preserve original applied controls across UI and pure helper replacement |

## Validation boundaries
- Linux/offscreen Qt and synthetic files/records only. No user's audio, credentials or live Serato database changed.
- Native macOS installation, signing/notarization, VoiceOver, Retina/large-text behavior and real Serato import require native validation. Qt offscreen is not a substitute.
- Real DJ musical quality/listening and calibrated corpus validation remain distinct from deterministic algorithm contract tests. No subjective artistic-quality certification is claimed.
- Spreadsheet UI interpretation is not manually certified; documented text import and serialized literal-cell checks cover the supported escaping convention.
- Noninterruptible third-party work may take time to finish while close remains responsive; it is never force-terminated.
- Whole-model/QAbstractTableModel rewrites are not necessary to close these findings; changes stay in reviewable local SDD/TDD slices.

## Integrated release gate
Pending current correctness-tranche gate, then remaining hardening slices and final exact-commit `uv run python scripts/release_gate_check.py --run`. Coverage threshold remains owned solely by `pyproject.toml`.
