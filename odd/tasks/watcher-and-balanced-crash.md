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
- Delivery: ask-on-risk; W1 work units have 184 authored changes (128 regression/recovery additions + 56 fix additions/deletions). Forecast W2 native diagnostic ~150 additional lines, excluding future causal fixes until evidence exists. No PR slices, PR creation, or merge authorized.

## Tasks

- [ ] **W1 — Reject stale watcher events.** Route: delegated writer (two non-trivial files). Capture watch identity/generation in callbacks, reject obsolete or inactive events, and prevent stale debounce state changes. First add tests for queued delivery after stop, pause, pause/resume, and folder replacement; require observed RED before production edits, then GREEN and full checks. Preserve valid current-watch events and existing suppression behavior. Rollback boundary: watcher event acceptance and its regression tests only.
- [ ] **W2 — Reproduce and resolve Balanced native crash.** Route: delegated bounded investigation, then implementation only if cause is established. Identify the actual launch revision/runtime, reproduce Balanced selection manually versus native accessibility inspection, preserve crash evidence, and test widget update/lifetime hypotheses. Acceptance: reproduce the original failure and demonstrate it absent after a causally supported fix; passing offscreen checks alone is insufficient.

## Evidence and current status

- PR baseline fetched and isolated feature branch created; original checkout and PR #360 unchanged.
- W1 preparation identified the queued-event lifecycle defect and proposed session-aware rejection. Eight regression cases cover queued events/retained callbacks and stale timeout delivery after stop, pause, resume, and replacement.
- Baseline functional attempt: targeted runner above exited **2**, before test collection. uv attempted Python 3.12.11 preparation but failed extracting `pip/_vendor/certifi/cacert.pem` with `Operation not permitted`. The managed permission profile restricts `.pem` paths. Do not work around it.
- Earlier direct Python execution and CodeGraph initialization were also blocked by host permissions. Native reproduction has not run.
- W1 regression/production delegated to watcher_writer; W2 causal mapping/diagnostic harness delegated to balanced_diagnosis. Static diff check passed. Native assessment command is blocked with exit 127; review remains unavailable, not approved or downgraded. RED is observed below; GREEN, full gates, native reproduction, and receipt remain pending.
- Regression commit: `b69be791beb24a7778a696fae9b72f9d12de38f1`; new remote branch verified. Observed RED: https://github.com/FmBlueSystem/XfinAudio/actions/runs/36858699561 — all eight added lifecycle cases failed for the intended behavior (obsolete events restarted debounce; invalidated timeout copied state). 3293 existing tests passed, 21 skipped, coverage 94.38%; pyright passed. Full wrapper stopped at its test failure, so later gates were not run. Git's default credential lookup was unavailable; push succeeded using the explicitly authorized gh credential helper for that command only, without modifying credential configuration or reading credential files.
- W2 native diagnostic baseline delegated to the same mapping worker: synthetic BuildScreen interaction under Cocoa in a separate test subprocess. This is a compatibility diagnostic, not an external AX reproduction or proof of fixing the original macOS 26.6.2 crash.
- W1 production edit made only after observed RED: capture source generation in each callback, retire it before source stop/join, reject inactive/obsolete event delivery, and guard pending debounce. Existing cross-thread test now uses the real source callback. Standalone Ruff check/format and diff checks passed. No observer/backend or suppression behavior changes. This does not promise protection from arbitrary fake timeout replay after a fresh event; the real adapter uses same-thread single-shot QTimer stop/restart semantics.
- W1 fix work-unit commit: `bdc19f6a76d9c40f040f466a9b3dca4edc579da1`. GREEN/full closure pending remote workflow. Native review assessment is unavailable; no approval/receipt is claimed.
- GitHub refused pushing the initial W2 workflow-file change because the authorized OAuth session lacks workflow scope. No scope refresh or credential replacement attempted. Candidate `59e6518` is preserved only on local branch `local/native-workflow-candidate`; current branch was restored to W1 commit and its workflow is unchanged.
- W2 harness prepared in tests/test_balanced_native.py only: an explicitly CI/branch-gated subprocess selects Cocoa before Qt import; the existing unchanged suite/workflow runs it. It asserts visible controls and a successful non-skipped Cocoa result, records exact runner/runtime/revision, and explicitly reports no external AX or own-process AX attribute coverage. The English synthetic fixture does not load the production translator or reproduce the reported Spanish label. No workflow files, CI scripts, permissions, or secrets are changed. Ruff check/format and diff checks passed; runtime execution pending.
- Diagnostic work unit: `3de5d74fed92db2e06eaa453716172c3922242c3`. First verification https://github.com/FmBlueSystem/XfinAudio/actions/runs/36860352618 failed at collection: helper import incorrectly omitted the existing tests package prefix. Corrected to `tests.test_build_screen` (consistent with existing test imports); this is a harness correction, not native crash evidence. No GREEN is claimed from this run.
- Verification https://github.com/FmBlueSystem/XfinAudio/actions/runs/36860592743 at `3b4e0e8d351073900e1ce3387a0907a6bcaaefeb`: eight watcher regressions passed; native Cocoa child passed one test on macOS 26.6.2 arm64, Python 3.12.10, Qt/PySide 6.11.1. Full suite had 3300 passed, 22 skipped, and two failures in scan-lifecycle recovery setup, so later full gates did not execute. Those tests manually invoked timeout without a pending event; the precondition is now established through immutable dirty-state replacement while preserving scan-completion/unavailable-watch assertions. Production invariant was not weakened.
- Native local computer-use inspection also failed before app access because its Node kernel was denied reading system OpenSSL configuration. No retry/bypass. Official Qt native synthetic accessibility table-element ownership is a targeted hypothesis only (https://code.qt.io/cgit/qt/qtbase.git/tree/src/plugins/platforms/cocoa/qcocoaaccessibilityelement.mm?h=v6.11.1); no causal fix or matching newer Qt release was established.
- Engram mirror: **pending**. The runtime hook reports no authoritative registered session identity and forbids agent-attributed memory writes. Preserve this local recovery document and mirror its full content under `odd/watcher-and-balanced-crash/tasks` only after the host restores session registration.

## Next step

Push the bounded W1 fix and separate W2 diagnostic work unit, dispatch the registered workflow, inspect GREEN/full gates and native baseline independently, and record exact commit/run evidence. Investigate W2 independently; do not claim W1 fixes the Cocoa crash or that native pointer testing proves external accessibility behavior.
