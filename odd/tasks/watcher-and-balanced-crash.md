# Watcher Event Lifecycle and Balanced Native Crash

## Objective and authorization

Fix stale watcher event acceptance and investigate the native Qt/Cocoa crash when selecting Balanced. The user authorized local implementation on 2026-10-01 and then explicitly authorized pushing a new branch to FmBlueSystem/XfinAudio and running its GitHub workflows using the current gh session. No PR #360 update, merge, release, audio mutation, live Serato writes, or credential inspection is authorized.

## Baseline and problem

- Repository: FmBlueSystem/XfinAudio.
- PR #360 baseline: `dd15f0dffb9d524169d9559e538e23afb23861a4`.
- Local branch: `fix/watcher-event-lifecycle`.
- Checkout: this isolated audit clone; the original checkout is untouched.
- `library_watch_service.py` accepts queued events after pause/stop and can restart debounce. Checking active state alone does not distinguish an old watch from a resumed or replacement watch.
- The supplied crash report shows main-thread EXC_BAD_ACCESS in Qt Cocoa accessibility. Its executing source revision remains unknown. The watcher defect is not established as its cause.
- AI shutdown is already guarded in this PR. Do not reimplement the main-branch shutdown fix or change the observer backend without causal evidence.

## Workflow and constraints

- Route: delegated direct ODD, with strict TDD from repository `AGENTS.md`. SDD has not been explicitly selected by the user.
- Mapping/preparation trigger: multiple controller, watcher, widget, and test files; delegated read-only preparation completed.
- Writer trigger: production and regression tests are two non-trivial files; one bounded writer prepares regressions first and waits for remote observed RED before production edits.
- Test runner: `uv run --locked pytest -q tests/test_library_watch_service.py tests/test_folder_watcher.py`.
- Closure: `uv run python scripts/release_gate_check.py --run`. The coverage floor belongs to pyproject.toml; never override it with the stale skill's CLI threshold.
- Remote verification: the existing `Non-audio release gates` workflow dispatched against the isolated branch on macOS. No changes to workflow permissions or secrets. First push contains regressions only; capture exact commit/run RED, then implement and capture GREEN/full gates on the fix commit.
- Native verification must use Cocoa, not offscreen Qt, with a fixture library and no external AI requests unless separately authorized/configured.
- RDD mode: unavailable; `gentle-ai review mode status --cwd <checkout>` is blocked by executable permissions. Do not infer disabled or low risk. Any future commit requires the native assessment/preflight under the existing user-owned switch.
- Delivery: ask-on-risk; forecast 150 authored changed lines for W1, W2 size unknown until reproduction. No commits or PR slices yet.

## Tasks

- [ ] **W1 — Reject stale watcher events.** Route: delegated writer (two non-trivial files). Capture watch identity/generation in callbacks, reject obsolete or inactive events, and prevent stale debounce state changes. First add tests for queued delivery after stop, pause, pause/resume, and folder replacement; require observed RED before production edits, then GREEN and full checks. Preserve valid current-watch events and existing suppression behavior. Rollback boundary: watcher event acceptance and its regression tests only.
- [ ] **W2 — Reproduce and resolve Balanced native crash.** Route: delegated bounded investigation, then implementation only if cause is established. Identify the actual launch revision/runtime, reproduce Balanced selection manually versus native accessibility inspection, preserve crash evidence, and test widget update/lifetime hypotheses. Acceptance: reproduce the original failure and demonstrate it absent after a causally supported fix; passing offscreen checks alone is insufficient.

## Evidence and current status

- PR baseline fetched and isolated feature branch created; source unchanged.
- W1 preparation identified the queued-event lifecycle defect and proposed session-aware rejection. Eight regression cases were added for queued events/retained callbacks and stale timeout delivery after stop, pause, resume, and replacement. Production code is unchanged pending remote RED.
- Baseline functional attempt: targeted runner above exited **2**, before test collection. uv attempted Python 3.12.11 preparation but failed extracting `pip/_vendor/certifi/cacert.pem` with `Operation not permitted`. The managed permission profile restricts `.pem` paths. Do not work around it.
- Earlier direct Python execution and CodeGraph initialization were also blocked by host permissions. Native reproduction has not run.
- W1 regression preparation delegated to watcher_writer; W2 read-only causal mapping delegated to balanced_diagnosis. Static diff check passed. Native assessment command is also blocked with exit 127; review remains unavailable, not approved or downgraded. No observed RED, GREEN, full gate, native reproduction, receipt, or completed task exists yet.
- Engram mirror: **pending**. The runtime hook reports no authoritative registered session identity and forbids agent-attributed memory writes. Preserve this local recovery document and mirror its full content under `odd/watcher-and-balanced-crash/tasks` only after the host restores session registration.

## Next step

Use the user-authorized remote branch and macOS workflow to obtain observed W1 RED before production edits. Investigate W2 independently with a synthetic library and native Cocoa evidence where feasible; do not claim W1 fixes the Cocoa crash or that offscreen tests prove accessibility behavior.
