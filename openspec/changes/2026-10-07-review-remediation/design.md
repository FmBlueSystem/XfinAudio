# Design decisions

Each decision names the alternative it rejected and why, in the order the work landed.

## D1 — Export names are reduced *and* contained (W1)

`safe_target_name` keeps only the final path component and rejects a request that leaves
nothing usable; the plan then resolves the chosen name against the export folder and
rejects anything whose parent is not that folder.

Reducing to a component alone was rejected: it would quietly write `../../x.txt` as `x.txt`
instead of telling the caller that the name was wrong, and a silent rename is harder to
notice than an error. Containment alone was rejected too, because it still lets
`a/b.txt` create a nested path inside the folder. The two checks together mean the function
is safe for a caller that ignores the plan, and the plan is safe for a caller that passes a
name the helper accepted.

## D2 — Only an in-flight *paid* request freezes the renderer field (W2)

`setRequest` returns early when `this.pending === 'ask'`, when the field is not editable for
the surface, when the value is not a string, or when it equals the staged value; otherwise
it resets the controller (clearing preview and consent) before staging the new text.

Freezing the field during `prepare` as well was rejected: preparation is local, costs
nothing and sends nothing, so an operator who edits an instruction while a local preview is
being built should not be blocked. Treating the case as a consent breach was rejected after
reading the gate: `gate.begin()` sets `busy`, the host's `canAct()` goes false, and the view
takes the local-hold path, so no request is ever sent with replaced text. The defect was
that `setRequest` called `reset()` (bumping the generation) mid-flight, so the authorized
result was dropped and the binding was lost; the fix keeps the binding and shows the hold
notice.

## D3 — The lock, not an edited input file, is the headless source of truth (W3)

`requirements-headless.txt` is now generated with
`UV_OFFLINE=1 uv export --frozen --no-dev --no-emit-project`, and
`desktop-electron/requirements-headless.in` was deleted. The regenerated snapshot is
601 lines / 33 pins, hash-locked, and both `packaging/{linux,macos}/requirements-build.in`
files consume it instead of a second copy.

`uv pip compile --generate-hashes` was rejected for this repository: it resolves against an
index and cannot run offline (`cffi==2.0.0 … unsatisfiable … network was disabled`), which
is exactly how the previous `.in`/`.txt` pair drifted. Keeping a hand-maintained `.in`
beside the lock was rejected because it re-creates the drift. `uv lock` was rejected because
it edits the lock rather than reading it.

Consequence, corrected during verification: the earlier claim in this section that
`packaging/{linux,macos}/requirements-build.txt` "cannot be regenerated in this offline
session" was wrong. `uv pip compile --generate-hashes` had only ever been attempted with
`UV_OFFLINE=1` present in the environment, and that variable — not the network — is what
refused the index (`cffi==2.0.0 … unsatisfiable`). Cleared of it, the documented compile
succeeds and the Linux lock is now a 37-pin export of the current snapshot. Two design
consequences came out of doing it: the compile resolves for the host platform unless told
otherwise, so the Linux lock is produced with `--python-platform linux` to keep the
Darwin-only `macholib` pin in the macOS file where it belongs; and guarding only the `.in`
inputs had left the file the freezer lane actually installs unguarded, so
`tests/test_headless_requirements_lock_drift.py` now fails if the compiled lock drops a
snapshot pin, contradicts a snapshot version, loses a hash, or stops recording its own
regeneration command.

## D4 — Documents are guarded like code (W4)

`tests/test_documentation_freshness.py` reads the tracked document set from `git ls-files`
and checks three things: referenced repository paths exist, `uv run <target>` resolves to a
declared console script or a known tool, and the AI settings document names controls that
the shipped renderer actually contains.

YAML is parsed with `tomllib`/text, never PyYAML, which is not a project dependency — the
same choice `tests/test_local_checkout_references.py` already made. The historical escape
hatch has two deliberately different shapes: a blockquote banner containing "historical"
inside the first twelve lines exempts a whole document, and the literal `(historical`
exempts one line. A bare `\bhistorical\b` head match was rejected after it wrongly exempted
`README.md` line 7, and capital `(Historical` deliberately does not exempt, which is why the
one fixture that used it was lowercased. Review notes, `odd/`, `openspec/` and the
architecture registry's own subjects are out of scope because they are evidence, not
instructions. The URL lookbehind exists so a published URL ending in `x.py` is not read as a
path in this checkout.

## D5 — Discarded failures are logged, not re-raised (W5)

`track_repository` logs one `WARNING` per unreadable profile and still returns `None`;
`scan_service` logs one `WARNING` when an audio MD5 signature cannot be read and keeps the
size/mtime freshness fallback. Tracebacks were rejected because a single bad file must not
abort a library scan, and promotion to `ERROR` was rejected because the scan succeeds.

The `except Exception: return None` sites in `audio/{danceability,tonal_profile,
spectral_profile}.py` were deliberately left alone: they implement the documented analyzer
contract where `None` means "not analysed", and changing them would change the contract
rather than observe it.

## D6 — The SDD state was reconciled, not advanced on the user's behalf (W6)

`openspec/changes/ai-playlist-improvement/state.yaml` moved from `status: apply` /
`verify: pending` to `verify` / `complete`, with a note recording who did it and that it
claims no approval; `next_recommended` stays `native-validation`, which no sandbox agent can
obtain. The skill's verification section now names
`uv run python scripts/release_gate_check.py --run` first and states that the coverage floor
lives in `pyproject.toml` and that `--cov-fail-under` must never be passed, because the flag
overrides the configured floor.

Rewriting the historical `ai-playlist-improvement` artifacts was rejected: they are the
record of what was true when they were written. Only provider-owned phase fields were
touched, deliberately, to stop them contradicting the artifacts beside them.

## D7 — Qt residue is deleted, and the deletion is guarded (W7)

Two shipped artifacts were deleted rather than hidden: the Qt Linguist catalogs
(`translations/*.ts` and the `assets/translations` wheel force-include) and the retired
Qt-dialog probe surface in `src/xfinaudio/ai/connection_test.py`. Git history retains both,
and nothing reads them: no `.qm` reader exists, no code or test referenced the catalogs, and
the probe module had zero `src/` callers while the live probe in
`headless/ai_execution.py` already sent the same text through the same client.

Two details were kept on purpose. `PROBE_MESSAGE` stays in `connection_test.py` because two
live headless modules import it, so its definition has one home and the guard can compare it
with the two Electron literals that whitelist it. `docs/ai-settings.md` was not marked
historical wholesale, because only its control names were Qt-era; the table below maps each
name it used to the control the shipped panel has, and the document's security statements
were already true.

| Document said (Qt dialog) | Shipped Electron panel |
|---|---|
| Settings → AI Settings / **Configure AI** action | the **Ajustes de IA** workflow panel |
| **Choose existing env file** | **Elegir archivo de credenciales…** |
| **Use default file** | **Quitar fuente de credenciales** |
| **Pressing OK** | **Guardar ajustes de IA** |
| **Cancel test** | the panel's cancel action / closing the panel |

`QT_QPA_PLATFORM: offscreen` was removed from both workflows: it existed to make a PySide6
test run headless, and no workflow imports Qt any more. The stale `__pycache__` tree under
the deleted `src/xfinaudio/desktop/` package was removed for the same reason a build
artifact is removed — it is untracked residue that made a removed module look present.

## D8 — Guard shape

Every fix that changes a shipped artifact landed with a test that failed first. The house
style was reused: text or regex parsing over generated files, `git ls-files` for tracked
sets, a `monkeypatch`-driven negative case proving the guard bites, and a docstring naming
the historical defect. RED was observed by reverting the fix or by writing the guard against
the unfixed tree and watching it fail, never by deleting a test. W8 is the one unit with no
functional RED — it closes a coverage gap against already-correct behavior — so it was
instead proved non-vacuous with a temporary probe that made the assertion fail, then
reverted.

## D9 — What was deferred and why

- The PyInstaller-freezer locks (D3): initially deferred as needing network access, then
  regenerated once the real cause (`UV_OFFLINE=1` in the environment) was found.
- The 62 changes parked at `status: verify`: archiving them is a process decision for the
  maintainer, not a defect a test can pin.
- Module splits and the duplicated `2..80` / 64-hex constants: real, but they are refactors
  with no observable defect, so they need their own change and RED.
- The dead `application/playlist_file_export.py` surface: it has no `src/` caller but six
  test files cover it, so it is an intentionally tested API, not residue.

## D10 — Review plan (the 400-line budget)

The advisory budget is 400 lines and this change is deliberately larger, because it is ten
independent findings from one review rather than one finding. The budget rule allows that
only with an explicit plan, so this is the plan: the diff is measured per work unit below and
each unit is reviewable **alone**, in the listed order, without reading the next one. No unit
depends on another's code; the only ordering constraint is that `W9` (this record) describes
units `W1`–`W8`, and `W10` records the verification of all of them.

Measured with `git diff --numstat` over tracked files plus `wc -l` over the untracked ones at
the time of writing:

| Unit | Scope | Files | +added | −deleted | Reviewable alone |
|---|---|---|---|---|---|
| W1 | export-name containment + guard | 2 | 120 | 2 | yes — one function and its 15 tests |
| W2 | renderer request immutability + labels + guards | 4 | 61 | 3 | yes — one class method, one view, 51 Node tests |
| W3 | headless snapshot, freezer inputs, regenerated lock + guards | 5 (+2 locks) | 250 (+1312) | 9 (+1576) | yes — the `.txt` locks are machine-generated |
| W4 | documentation freshness guard, banners, registry, config/skill truth | 24 | 646 | 139 | yes — 20 of the 24 are one-line banners |
| W5 | discarded-failure logging + guard | 3 | 162 | 27 | yes — two `Logger.warning` sites and their tests |
| W6 | SDD state/config reconciliation | 4 | 46 | 21 | yes — YAML/text only |
| W7 | Qt residue removal (workflows, pyproject, AI probe state machine, docs, catalogs) | 11 | 76 | 5207 | yes — deletions are generated catalogs and dead code |
| W8 | real-core improvement integration test | 1 | 113 | 0 | yes — one test file, no production change |
| W9 | this SDD record | 7 | 740 | 0 | n/a — the review artifact itself |
| W10 | gate + Electron app launch evidence | 4 | 110 | 9 | yes — regenerated evidence and its script |

Totals: **+2324 / −5417 reviewable lines**, of which the two machine-generated lock files
contribute +1312 / −1576 and are excluded from review as generated output; the largest
deletion block is 4 996 lines of generated `.ts` translation catalogs plus `.qm` binaries
removed in W7. The authored production surface is therefore `src/` (W1, W5, W7: 3 files),
`desktop-electron/renderer` (W2: 2 files), `pyproject.toml`, two workflow files and four lock
or requirements files; everything else added is tests (W1–W8) or this record (W9).

Suggested review order and the question each unit answers: W1 — *can an export name escape
its folder?*; W2 — *can a local edit overwrite an in-flight paid request?*; W3/W5/W7 — *does
the tree still install, log and ship what it claims?*; W4/W6 — *do the durable documents
describe the tree that exists?*; W8 — *is the improvement/save path covered against the real
core?*; W9/W10 — *is the evidence for all of the above reproducible?*

Chained-PR recommendation stays **false** for one reason: the units are sequential findings of
a single review session on one branch (`feat/ai-playlist-improvement`), and splitting them
into separate PRs would separate each fix from the test that proves it and from this record.
The maintainer can still land them as separate commits — the delivery section of `tasks.md`
lists the order — and a reviewer who wants a narrower diff can read the table row by row.
