# Design: harden-release-gates

## 1. What a gate is allowed to read (B1)

The gate read the working tree. The publication path reads archive members. Those are different
trees, so the gate could fail over a file that could never be published and — more importantly —
pass over one that could, if it had been force-added.

Decision: the gate reads the **index** (`git ls-files`), because the index is the publication
tree. It is exactly the set of files packaging starts from, and it is the thing a contributor
actually controls. `.gitignore` alone would not have been enough, because a force-added file
overrides it.

Rejected: teaching the gate to ignore `.DS_Store` and the private handoff names. That fixes one
file and leaves the class — the gate would still be reading a tree nobody publishes.

Rejected: deleting the offending `.DS_Store`. It turns the gate green on one machine while the
gate remains satisfiable only by local housekeeping, which is the complaint.

The oracle is pinned in both directions inside a throwaway repository — an ignored file present
and passing, a force-added file present and failing — so the test proves the rule rather than the
current state of this tree.

## 2. One owner for the coverage floor (B4)

The floor existed twice: `fail_under = 70` and `--cov-fail-under=70` on the command line. The
flag wins, so the configuration was decorative in the one place a maintainer would edit.

Decision: the flag is removed and `pyproject.toml` owns the number, raised to 89 against a
measured 91.64%. The 2.6 points of headroom are deliberate slack for ordinary churn; the old 70
could absorb a twenty-point collapse before anyone noticed, which is not a floor.

The guard refuses the flag's return and refuses a configured floor below 85, so the number cannot
drift back down without a failing test.

## 3. What a source package is for (B5)

A real `uv build --sdist` shipped `PLAN.md`, the `PLAN-REVIEW-LOG*` files and every document under
`docs/reviews/`, including the loudness multi-agent design reviews.

Decision: exclude them from the build **and** refuse them in the inspection. Detection alone would
have been too late — the point is that the archive never contains them. The documents stay in git;
they stop being distributed. A source package exists to build the product, not to carry working
notes.

Rejected: extending `FORBIDDEN_FILE_NAMES` only. That is detection without prevention, and it
would let the same mistake ship again the moment someone edited the exclude list.

## 4. The publication path (B2)

The workflow ran `pytest -q`, then built and published. Every other guarantee in this repository
was enforced on pull requests and skipped on the one path that reaches the public index.

Decision: the workflow runs `scripts/release_gate_check.py --run` — the same gate the pull-request
path runs — and asserts the tag against `pyproject.toml` before building. The drift is not
hypothetical: v1.0.2 named a build 265 commits newer than the version it published.

The suite is no longer invoked separately, because the gate already executes it once; a test reads
the workflow's `run:` blocks rather than grepping the file, so a comment mentioning a command is
not mistaken for an invocation.

## 5. One repository (E1)

Three live files pointed at a second, independent clone: the OpenSpec config named it as
`project.root`, the restart handoff told a human to re-open it, and a stray test script put its
`src` on `sys.path` — which is why that script only ever worked on one machine. Both defects had
already been recorded and deferred twice, in the archive reports of
`2026-07-20-strategy-ux-clarity-and-dedupe` and `2026-07-18-recommendation-scoring-correctness-fixes`.

Decision: `project.root` becomes `.`, matching how the tooling resolves the root
(`git rev-parse --show-toplevel || pwd`). The handoff is marked as a historical record. The dead
script is deleted: pytest never collected it, nothing imported it, and it carried a second stale
defect of its own.

A guard now refuses any tracked file outside the historical record that names that checkout, so the
next pointer cannot be added quietly. `openspec/changes/` and `docs/reviews/` are exempt because
they record what happened rather than instructing a reader — and because the guard is itself
tracked, so a literal path in its own source would make it flag itself.

## 6. Documentation that restates an owned value

Removing the flag from the gate command left the same flag in `AGENTS.md`, the file a contributor
is told to follow. Following the documented sequence would have lowered the floor from 89 to 70 —
the defect removed from the command, left behind in the instructions.

Decision: the sequence runs `pytest --cov -q` and the section states that `pyproject.toml` owns the
floor. The guard is scoped by artifact shape rather than by convenience: the flag is asserted
against the **commands**, because the surrounding prose names `--cov-fail-under` precisely in order
to forbid it, and the pointer to the owner is asserted against the whole **section**, because that
guidance belongs in prose.

## 7. Artifact layout

`AGENTS.md` requires an active change to contain `spec.md`; the repository's established delta
convention places normative text at `specs/<capability>/spec.md`. This change satisfies both
without duplicating the requirements: the two capability deltas carry the normative text and
`spec.md` is an index that names them.

## 8. Testing

Every guard is pinned by a test that fails when the guard is removed. Two guards can be driven in
both directions and are: the publication gate (an ignored file passes, a force-added file fails)
and the documented sequence (a reintroduced flag fails, a removed pointer fails). Where a guard
reads a file, its test reads the same file's `run:` blocks or parsed configuration rather than
grepping prose.
