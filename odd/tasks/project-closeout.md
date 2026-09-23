# ODD feature ledger — project-closeout

**Branch:** work happens on `main` (integration) — merges land directly per user decision
**Worktree:** `/Users/freddymolina/Desktop/XfinAudio/repo`
**Runtime:** macOS, Python 3.11 (`.venv/bin/python`), `uv`
**Multi-model routing:** `.pi/subagents.json` project pin — writer=`nan/deepseek-v4-flash`, verify=`nan/qwen3.6`, explore=`nan/qwen3.8-flash`, judges/reviewers per family diversity (see mem #6860). `glm5.3` non-flash is NOT in the nan subscription (401).

## Why

User decision (2026-09-23): close every pending item of the XfinAudio project.
Orchestrator = parent (glm5.3-flash); code written by DeepSeek via nan; verification by independent models.

## User decisions recorded

- **Integration:** direct local merges to `main`, suite green per step, push at the end.
- **Cost regression (arc-subset-sequencing):** accept and document. Raw/batch mode 4.7x total (worst anchor 13.7x) is accepted because the user never waits on batch; the real UI path measured ~1.0x (worst case 0.6s per recommendation including pool planning). Measurement evidence: mem #6857.

## Pending inventory (validated 2026-09-23)

| ID | Item | Status |
|---|---|---|
| P1 | Pin multi-model subagent routing | DONE (config written, mem #6860) |
| P2 | Merge 3 branches to main: harden-release-gates → arc-subset-sequencing → verified-product-defects | in progress |
| P3 | Document cost-regression disposition in arc-subset-sequencing artifacts | pending |
| P4 | Fix test packaging path resolution (DeepSeek, TDD) | DONE — commit pending at P4 close |
| P5 | Archive `add-loudness-module` + `library-file-watcher-rescan` (both verified) | pending |
| P6 | Minor recorded defects: `openspec/config.yaml:116` skill-registry pointer unresolvable; AGENTS.md redundant coverage step | pending |
| P7 | Push main, close session | pending |

## Work unit commits

(recorded as they land)

## Work unit commits (final)

- `3949a85` merge: chore/harden-release-gates (9 commits) — suite 1897 green
- `efee27b` merge: feat/arc-subset-sequencing (8 commits) — suite 1922 green
- `21ecb8b` merge: fix/verified-product-defects — suite 1924 green
- `c230b3f` docs(openspec): accepted cost disposition for arc-subset-sequencing (P3)
- `576d5d5` test(packaging): resolve change artifacts wherever the change lives (P4, DeepSeek TDD)
- `fbe72ff` docs(openspec): archive the four verified changes + sync spec deltas (P5, DeepSeek)
- `aed78fe` fix(config): skill-registry pointer + AGENTS.md verification sequence (P6, DeepSeek)

Suite final: 1926 passed, ruff clean. Pending: push (P7).
