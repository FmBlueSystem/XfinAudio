# Restart Handoff — XfinAudio

Date: 2026-09-24
Status: **current instructions**, not a historical record. The earlier
`docs/restart-handoff-2026-06-03.md` is kept for the record; this file is meant to be
executed by the next session.
Git status: `main` at `db94d6f`, equal to `origin/main`, working tree clean except one
untracked file: `odd/tasks/review-warning-remediation.md` (the ODD ledger for the work
described below; `odd/tasks/` is untracked by convention in this repository).

## Current state

The repository is green and the native review remediation is finished:

```text
.venv/bin/python -m pytest -q                          # 1955 passed
.venv/bin/python -m ruff check .                       # All checks passed
.venv/bin/python -m ruff format --check .              # 312 files already formatted
.venv/bin/python -m pyright --pythonpath .venv/bin/python   # 0 errors
```

Six WARNING and twelve SUGGESTION advisory findings from three reviewed candidates are
closed in nine commits, plus one live defect the review never found (a one-shot iterator
consumed twice in `_beam_arc_subset_path`, which made a buildable arc report as
infeasible). Three findings were refuted as false positives rather than fixed.

The full narrative, per-finding evidence, and the exact RED/GREEN output live in
`odd/tasks/review-warning-remediation.md`. Read it first.

## The one outstanding task

Run the native review preflight (Receipt-driven development is **on** globally, decided by
the global scope) over the nine commits written *after* the last reviewed range. This is
new, unreviewed work.

| | |
| --- | --- |
| Candidate | `c251c41..db94d6f` |
| Base ref (a full 40-character commit id is required) | `c251c41ae78def5be313859d0f4c60e08e74cc7b` |
| `workspaceRoot` | `/Users/freddymolina/Desktop/XfinAudio/repo` |
| Size | 9 commits, 13 files, 710 insertions, 41 deletions |
| Commits | `fdb5ce2`, `7ed71a2`, `37b1891`, `bf5d197`, `0fb5d20`, `797f96e`, `72a76bc`, `a2db9f9`, `db94d6f` |

**Definition of done.** The task is done when the agent has either (a) burned an approved
authority for this candidate by running the exact provider-issued acknowledgement, or
(b) relayed a stop it cannot resolve and asked the human. "I inspected the candidate" or
"I started the review" are not done: a lineage left in `reviewing` is an open transaction.

## How I validated and improved the instruction

The instruction given was: *"write a .md with the instructions, I restart the machine and
the agent handles what is left."* The handoff-document mechanism is right and is what this
file implements. Five corrections:

1. **A machine restart is not required.** Only the Pi host process holds the stale session
   state; quitting and reopening the Pi session is sufficient and much cheaper. A machine
   restart also works, but it is not the minimum action.
2. **A restart only helps if the environment variable is unset in the shell that launches
   Pi.** If `GENTLE_PI_SKIP_GENTLE_AI_INSTALL` is set, the package installer *skips silently*
   — that is the failure that produced this handoff, and a restart alone would not fix it.
   Check it in the preflight below.
3. **"Handles what is left" needs a definition of done**, otherwise the agent stops at the
   first stop code and asks anyway. Defined above.
4. **The agent cannot finish this alone.** Every medium- or high-risk candidate needs a
   host-side consent answer from the human. Expect one or two prompts; the answer tokens are
   exactly `granted` and `declined`. Budget for answering them.
5. **The instruction should say what to do when the review finds something**, because it
   will. This session's equivalent review produced eighteen findings across three
   candidates. The protocol is in the next section.

## What to do when the review produces findings

The same protocol used for the previous rounds, in order:

1. **Re-derive before believing.** After a lineage is burned, the native store drops the
   lineage and the reviewers' prose is **unrecoverable**; only finding id, lens, severity and
   exact `file:line` survive. Re-derive each finding from the code. An honest "false
   positive, here is why" is a successful outcome — three of this session's twelve advisories
   were refuted, and inventing a change to look busy is the failure mode to avoid.
2. **Batch by blast radius and keep writes single-threaded.** One writer at a time. CI and
   docs first, shipped code last.
3. **Strict TDD**: write the red test first and *observe* it fail for the intended reason
   before the production edit. A red run you did not see is not evidence.
4. **Verify with a different model family than the writer.** Adversarial roles must not
   share the writer's family, or the verification is self-confirmation.
5. **Commit each batch as a work unit** (fix + test + doc together), Conventional Commit
   message. Pushing is a separate, human decision unless the human has said otherwise.

## Preflight — run these first (about thirty seconds)

```bash
cd /Users/freddymolina/Desktop/XfinAudio/repo
git rev-parse --abbrev-ref HEAD            # expect: main
git rev-parse HEAD                         # expect: db94d6f...
env | grep -i GENTLE_PI || true            # must NOT list GENTLE_PI_SKIP_GENTLE_AI_INSTALL

GA="$HOME/.pi/agent/npm/node_modules/gentle-pi/.gentle-ai/v3.7.0/gentle-ai"
"$GA" --version                            # expect: gentle-ai 3.7.0
"$GA" review mode status                   # expect: receipt-driven development: on

# Prove the package-local binary resolves in a fresh process. If this works but the
# review tool still reports it missing, the running session holds stale state and only a
# session restart clears it.
cd "$HOME/.pi/agent/npm/node_modules/gentle-pi" && node --input-type=module -e "
import * as m from './runtime/gentle-ai-binary.mjs';
console.log(m.resolveGentleAiBinary(process.cwd(), process.platform));"
```

If that last command prints a path but `gentle_review inspect` still answers
`native-status-package-binary-missing`, do **not** start a transaction. Restart the Pi
session and repeat. If the resolver fails, re-run the installer from the package directory:
`node scripts/install-gentle-ai.mjs`.

## The lifecycle — facade first, never invent an operation

The compact facade (`gentle_review`) owns inspect, START, consent, bound STATUS and
acknowledgement. Captures go through `gentle_review_capture_group` (or
`gentle_review_capture` for a single slot). Provider-issued bindings are authoritative and
opaque: copy them exactly, never hand-build or "fix" them.

1. **Inspect.** `gentle_review` with `operation: "inspect"`, `input` as a *JSON string*
   — `{"baseRef": "c251c41ae78def5be313859d0f4c60e08e74cc7b", "committedOnly": true}` —
   and `workspaceRoot` the repository. Expect a fresh-target result carrying
   `next_transition.execute.command`.
2. **START via the returned command.** A base-ref candidate is started with the native
   invocation the inspect returned (the facade's `start` does not take a base ref); it ends
   with `--consent=relay`. Run it verbatim. It returns the typed
   `gentle-ai.review-integration.consent/v3` envelope.
3. **Relay the consent envelope losslessly** to the human: keep the provider's headline,
   reason, value, risk evidence, choice labels and every choice `effect` in the user's
   language, but keep the machine answer tokens (`granted`, `declined`) and the
   `consentBinding` untouched. Use one single-select question. Then run the exact
   invocation printed in the chosen choice — do not edit tokens, target ids or ids.
4. **Collect.** `gentle_review` `operation: "status"` with the retained `lineageId` and
   `workspaceRoot` returns `collectBindings`. Pass **every** entry to
   `gentle_review_capture_group` with the same `lineageId` and `workspaceRoot`. The first
   call returns a cost forecast and runs nothing; resubmit the same bindings plus
   `reviewerRunAcknowledged: true` to actually run the reviewers.
5. **Acknowledge exactly.** On `approved`, the closure envelope carries an
   `acknowledge-approved` command with a `--token=...`. Run it verbatim. Its successful
   return burns the authority. **Do not call STATUS after the burn.**

Expected shape: risk tier `high`, four lenses (`review-risk`, `review-resilience`,
`review-readability`, `review-reliability`), each lens one model run.

## If it stops before approval

| Stop | What it means | What to do |
| --- | --- | --- |
| `lens_context_budget_exceeded` | The reviewer evidence exceeds the native context budget. It is measured in prompt **bytes**, not diff lines: 9,040 lines of docs passed while 3,909 lines of Python failed. | Split the candidate into smaller ranges. Detached worktrees inside the repo at the intermediate merge commits worked: `git worktree add .review-slice-1 <commit>`, inspect from there, then `git worktree remove` when done. |
| `managed_assets_outdated` | The managed assets predate the installed binary (this repository's state recorded 3.6.1 while the package now carries 3.7.0). | Run the exact `gentle-ai sync` command the stop prints, then re-query STATUS. Do not run `sync` pre-emptively: it writes managed assets such as `AGENTS.md`, and that is the human's decision. `sync` has no dry-run. |
| `rdd_disabled` | The review switch is off for this clone. | Run the exact source-scoped enable command the stop prints. |
| `unchanged_or_unverified_authority`, `empty_base_diff_bootstrap_required`, `manual_intervention_required` | Terminal, or needs a maintainer decision. | Report it and stop. Do not attempt recovery on your own. |

## Operational lessons that cost hours; do not rediscover them

- **`~/.pi/gentle-ai/models.json` is a FLAT map per role**, for example
  `{"review-risk": {"model": "nan/glm5.3-flash", "thinking": "high"}}` — not nested under a
  `ranks` key. The harness rewrites the file to this flat shape; writing it nested silently
  breaks reviewer routing with "no model is configured for review-X".
- **`review-reliability` truncates with `stopReason: length`** at `thinking: medium` or
  `high`. With `thinking: low` it completes. This exact failure cost two full reviewer runs.
- **The capture tool accepts only the facade's `collectBindings` (camelCase, carrying the
  `agent`/`materialize` arguments and the `submission` block).** The native CLI's
  `review status --next-transition` returns a snake_case shape with the same values, and
  submitting those is rejected as "unknown, expired, or from different session routes".
- **A failed group admits nothing** (`prepared_reviewers: 0`). Call fresh STATUS and resubmit
  the whole group; it re-forecasts and then runs. Never replay reviewer bytes from a
  transcript.
- **`git log -S <name>` gives substring false positives.** Searching `_arc_subset_path`
  matched `_exact_arc_subset_path` and `_beam_arc_subset_path`. Use `git grep -w`, `hasattr`,
  or `git log -S "def <name>"` to ask whether a symbol ever existed.
- **Use `.venv/bin/python` for every test run.** The system `python3` lacks pydantic. `uv` is
  not guaranteed on this machine, so `uv run` in older documents is stale.
- **pyright needs the interpreter**: `.venv/bin/python -m pyright --pythonpath .venv/bin/python`.
  Without the flag it reports about thirty false `Import "pydantic" could not be resolved`
  errors.
- **A guard that cannot fail is not a guard.** This repository produced two of them: a test
  that monkeypatched a symbol which never existed (`raising=False` makes the patch silently
  inert) and a config guard that matched one literal spelling and passed whenever the key was
  absent. When writing or reviewing a guard, ask what would have to break for it to fail. If
  the answer is "nothing", it is decoration.

## What NOT to do

- Do not hand-build or edit a provider-issued `target`, `target-evidence`, `subject-hash`,
  `repository-context`, `lineage` or `collectBinding`. Copy them exactly.
- Do not start a lineage you cannot collect from in the same session. That strands an open
  transaction.
- Do not treat a `stop` as approval, and do not claim delivery because "the review is closed":
  after the acknowledgement the lifecycle ends, and commit, push, pull-request and release
  remain ordinary repository decisions.
- Do not invent a defect to justify a finding you cannot substantiate. Refute it in writing.
- Do not commit, push or run `gentle-ai sync` on your own initiative if the human has not
  authorized it in this session.
- Do not write generated technical artifacts in Spanish: code, comments, tests, commit
  messages and repository documentation default to English regardless of the conversation
  language.

## Recommended next steps after restart

1. Read `odd/tasks/review-warning-remediation.md` (untracked, on disk) for the full history.
2. Run the preflight above and confirm the environment is no longer stale.
3. Run the native review for `c251c41..db94d6f` through the lifecycle above, relaying the
   consent envelope to the human.
4. If it approves with advisory findings, handle them with the protocol above, one writer at
   a time, each batch verified by a different model family.
5. If it stops with `lens_context_budget_exceeded`, split by commit ranges rather than by
   guessing: this candidate is 9 commits and 710 insertions, which is well under the budget
   that previously failed at 3,909 lines of Python.
