# 2026-09-30 audit remediation matrix

Scope: shared application correctness/security, Serato export workflows, musical algorithm contracts, and measured incremental reliability/performance improvements. Other DJ exporters are preserved but their specific enhancements are excluded by owner request. Changes remain local; no push, pull request, release or deployment is authorized.

Status vocabulary: **Implemented** = regression-tested focused slice, still subject to the final integrated gate; **In progress** = planned/being implemented; **Accepted** = intentional product behavior; **Excluded** = owner-scoped out; **Blocked validation** = requires unavailable native/external environment, not an untested claim of success.

| Audit finding | Status | Change / evidence |
|---|---|---|
| S1 credential-bearing HTTP/redirects | Implemented | HTTPS-only final endpoints, all redirects rejected, non-forwardable Authorization; offline transport matrix |
| S2 formula-like metadata in CSV | Implemented | Shared literal text encoding for playlist, metadata checklist and readiness CSV; raw JSON/numeric fields unchanged |
| S3 non-Serato filename containment | Excluded | Owner explicitly limited export improvements to Serato; other exporters untouched |
| Loudness overwrites comments automatically | Accepted + disclosure fixed | Default-enabled combined analysis/write-back preserved; truthful docs and visible English/Spanish settings disclosure; corrupt-settings recovery alone pauses writes |
| Local DMG build can skip exact-source gate | Implemented | Fail-closed clean-SHA full gate before fresh/reused app packaging, source rechecks, version/content/mode/link integrity and staged-bundle verification |
| GitHub Actions version tags mutable | Implemented | All eight workflow action references pinned to reviewed immutable upstream commits |
| FFmpeg signature fetched but unused | Implemented | Download only the pinned-hash verified archive; no implied signature verification |
| CQ1 close during active work aborts | Implemented | Asynchronous owned-thread drain; ten subprocess scenarios; no forced terminate |
| CQ2 settings truncation/unrecoverable startup | Implemented | Temporary fsync + atomic replacement, preserved invalid bytes + visible recovery, typed UI failures, recovery-only write-back pause |
| CQ3 stale rescan dirty state | Implemented | Publish cleared state through shell owner; integration assertion |
| CQ4 orphan playlist references | Implemented | FK enforcement per connection + idempotent orphan migration preserving valid order |
| CQ5 connection lifetime depends on GC | Implemented | Transaction context closes explicitly; 100 reads with GC disabled add zero descriptors |
| CQ6 quadratic completion/UI-row work | Implemented | Immutable tick batches, one row-index pass, sorting suspension per batch, terminal flush and safe teardown; reproducible 1k/10k/50k synthetic replay |
| CQ7 weak mutable/type state contract | Implemented | Frozen fields, unknown-name rejection, current-snapshot publication and typed callback boundary; shallow immutability and update-value runtime-validation limits documented |
| Runtime source/wheel translations/icons missing | Implemented | Shared runtime resolver, icons/QM included in wheel; extracted wheel loads real catalog |
| Linux vanished-folder watcher failure | Implemented | Recoverable watcher warning; fixture directory created; scan completion still finishes |
| Linux narrow Color-column failure | Implemented | Compact Library layout/columns; focused original regression passes |
| F1 generated Apply action hidden | Implemented | Visibility every render, default balanced selection, explicit track-count CTA |
| F2 1000x700 window impossible | Implemented | Generated/applied workflow measured exactly 1000x700; short-display control scrolling and wider prompt |
| F3 inconsistent anchor eligibility | Implemented | Shared complete-anchor eligibility and direct starting-track/repair navigation; AI no-anchor route remains valid |
| F4 fractional BPM truncated | Implemented | Shared precision-preserving display across Library/Review/metadata |
| F5 destination/next-step clarity | Implemented / partly Excluded | Direct Serato crate and backup paths distinguished from optional report folder; no separate staging folder required; other-software enhancements excluded |
| F6 missing-data worklist buries repairs | Implemented | Incomplete default, human labels, repair checklist + refresh; independent Library filters; one Serato worklist dispatch per click |
| F7 synchronous Prep/no visible generation cancel | Implemented | GUI-safe worker, progress, visible Cancel, cooperative checkpoints, retry/stale-result protection and preserved prior/applied work |
| F8 tooltip-only explanations | Implemented | Build details and selectable keyboard-accessible Review track/transition explanations; compact layout and clear/reorder handling tested |
| Folded BPM reachability drops valid edges | Implemented | Interval-neighbor graph traversal matches independent all-pairs oracle on 20,000 synthetic corpora |
| Count cap drops locked/end controls | Implemented | Mandatory controls preserved before sequencing; infeasible caps diagnosed |
| Duration round-down silently underfills | Implemented | Actual per-track duration coverage and explicit shortage/unknown-duration diagnostics |
| Prep prefix trimming drops end/locks | Implemented | Count applied before sequencing; exclusions before candidate cap; counts above 25 supported |
| Invalid zero/negative/nonfinite BPM accepted | Implemented | Finite-positive parse/fallback contract, defensive legacy scoring and readiness blocking |
| Camelot diagonal direction/explanation wrong | Implemented | Primary-source directional rule, full 24-key truth table, semitone vs whole-step lift descriptions |
| Replacement/backfill can restore excluded tracks | Implemented | Preserve original applied controls, exclusions and strategy eligibility across UI and pure-helper replacement |

| Serato overwrite/incomplete-write recovery | Implemented | Validate payload and file identity, atomic replacement, unique recoverable backups, readback recovery, safe explicit rollback and symlink rejection; no database V2 writes |
| Redundant local-search scoring under coverage | Implemented | Score the unchanged incumbent once per pass; deterministic operation-count RED/GREEN without relaxed time thresholds |
| New critical UI translation coverage | Implemented | English/Spanish Prep, Review, direct Serato destination and loudness disclosures; both shipped QMs rebuilt and loaded by runtime tests |

## Validation boundaries
- Linux/offscreen Qt and synthetic files/records only. No user's audio, credentials or live Serato database changed.
- Native macOS installation, signing/notarization, VoiceOver, Retina/large-text behavior and real Serato import require native validation. Qt offscreen is not a substitute.
- Real DJ musical quality/listening and calibrated corpus validation remain distinct from deterministic algorithm contract tests. No subjective artistic-quality certification is claimed.
- Spreadsheet UI interpretation is not manually certified; documented text import and serialized literal-cell checks cover the supported escaping convention.
- Noninterruptible third-party work may take time to finish while close remains responsive; it is never force-terminated.
- Whole-model/QAbstractTableModel rewrites are not necessary to close these findings; changes stay in reviewable local SDD/TDD slices.

## Integrated release gate
The recovered correctness tranche at `6f7a769` passed all automated gates: 2,775 tests, 93.49% coverage, clean types/lint/format, smoke, source/wheel hygiene and PyInstaller check-only. All remaining slices are now integrated; the final combined exact-commit `uv run python scripts/release_gate_check.py --run` remains pending. Coverage threshold remains owned solely by `pyproject.toml` (89%).
