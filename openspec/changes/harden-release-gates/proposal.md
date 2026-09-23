# Proposal: harden-release-gates

## Intent

Five guards in this repository do not protect what they claim, and the publication path with
the least scrutiny — the tag push that publishes to PyPI — is gated by almost nothing. Every
defect below was found by running the guard, not by reading it, and every one of them fails in
the direction that matters: the guard reports success over an artefact nobody would accept.

## Why

| ID | Defect | Evidence observed before the change |
|---|---|---|
| B1 | `tests/test_publication_artifact_hygiene.py` scanned the **working tree** with `PROJECT_ROOT.rglob`, so any git-ignored `.DS_Store` failed it. It runs inside `scripts/release_gate_check.py`, which is inside the mandated `AGENTS.md` verification sequence. | `uv run pytest -q` → `1 failed, 1733 passed`. `git ls-files \| grep DS_Store` → 0. The real publication path (`scripts/source_package_hygiene_check.py`, which inspects actual sdist members) already excluded `.DS_Store`, so the gate failed while nothing publishable was affected. |
| B2 | `.github/workflows/publish-to-pypi.yml` ran only `uv run pytest -q` before `uv build` and `uv publish`: no type check, no lint, no coverage floor, no release gate, and no check that the tag agreed with `pyproject.toml`. | the workflow's own steps. The pull-request workflow gated all of it; the path with no reviewer gated almost nothing. |
| B4 | `[tool.coverage.report] fail_under = 70` against a measured 91.64%, and the same 70 passed again as `--cov-fail-under=70` in the gate command. | measured on `main`: `TOTAL 11332 947 91.64%`. Because the flag wins over the config, raising the configured value alone changed nothing. |
| B5 | A real `uv build --sdist` shipped planning scratch: `PLAN.md`, the `PLAN-REVIEW-LOG*` and `PLAN-docs-audit-*` files, and every document under `docs/reviews/`. | verified with a real `uv build --sdist` plus a diff against `git ls-files`. The hygiene script's `FORBIDDEN_FILE_NAMES` did not cover them, so the gate reported PASS. |
| E1 | `openspec/config.yaml` set `project.root` to `/Users/freddymolina/Documents/audio` — a different, independent clone of this repository, 324 commits behind on a branch of its own. | that path was its own git checkout. Two further live files pointed at it: `docs/restart-handoff-2026-06-03.md` told a human to re-open it, and a stray test script put its `src` on `sys.path`, which is why that script only ever worked on one machine. |

## What Changes

1. The publication hygiene gate inspects the **index** (`git ls-files`) instead of walking the
   filesystem.
2. The coverage floor has **one** definition, `pyproject.toml`, raised from 70 to 89, with the
   command-line flag removed from the gate command.
3. The sdist **excludes** planning and review scratch, and the inspection refuses those paths, so
   detection is the second line of defence rather than the first.
4. The publish workflow **runs the release gate** before building and **refuses a tag that
   disagrees with the project version**.
5. `openspec/config.yaml` describes **this** repository, and a guard refuses any tracked file
   outside the historical record that names another local checkout.
6. The verification sequence in `AGENTS.md` stops documenting a coverage floor that
   `pyproject.toml` owns.

## Capabilities

### New: release-gate-integrity

A gate must inspect the tree that actually gets published and must not be satisfiable by local
circumstances; the coverage floor must have exactly one owner; the source distribution must carry
product source rather than working notes; and the publication path must be gated at least as
strongly as the pull-request path.

### New: repository-reference-integrity

No operational file in this repository may direct a reader or a tool at a different checkout of
this repository, and a documented procedure must not restate a value that another file owns.

## Impact

- **The mandated verification sequence changes behaviour.** `AGENTS.md` requires
  `scripts/release_gate_check.py --run`; that gate now reads `git ls-files`, so a contributor with
  a git-ignored `.DS_Store` at the repository root passes where the gate used to fail. That is the
  intended fix, not a relaxation: the file was never publishable.
- **A higher bar for every later change.** The floor moves 70 → 89 against a measured 91.64%.
- **What the published source package contains.** `docs/reviews/` and `docs/superpowers/` stay in
  git and stop shipping, so the loudness multi-agent review evidence is no longer distributed in
  the sdist.
- **No product behaviour changes.** No file under `src/xfinaudio` is modified by this change. The
  wheel was never affected: none of the excluded scratch lived inside `src/xfinaudio`.
- **Out of scope.** Independent review of the change itself; archiving the two changes whose
  `state.yaml` already records `next_recommended: archive`; and the follow-ups recorded in the
  orchestration ledger (a dead `conventions.skill_registry` pointer, and a packaging test that
  reads an active change's artifact and therefore breaks when that change is archived as
  prescribed).
