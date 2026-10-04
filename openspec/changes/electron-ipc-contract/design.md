# Design

## Architecture impact

None. The change is one arm inside an existing `switch` in the Electron main process. The trust
boundary is unchanged: `action()` calls `validateRequest(method, raw)` first (`main.ts:103`), and
`validateRequest` throws `Unsupported action` for any method absent from its merged allowlist
(`security.ts:49`). The `default:` arm only converts "allowlisted but undispatched" from a silent
`undefined` resolution into a rejection. No module boundary moves, no type is introduced, no
dependency changes.

## Affected files (apply phase — not yet authorized for this session)

| File | Change | Lines |
|---|---|---|
| `desktop-electron/src/main.ts` | Add `default:throw new Error('Unsupported action');` as the final arm of the `action()` switch (after `main.ts:180`, before the switch close at `main.ts:181`) | +1 |
| `desktop-electron/tests/ipc-contract.test.mjs` | New focused guard test | ~45 |

Total ~46 changed lines, within the 400-line review budget.

## Guard test design

Follows the existing repo convention in `desktop-electron/tests/restored-wiring.test.mjs`, which
already reads `src/main.ts` and `src/preload.ts` as text and requires `case 'x':` and
`invoke('x'` to exist per method. The new test combines that structural convention with a runtime
probe against the compiled validator.

Extraction (all from source text, no new dependency; only `node:test`, `node:assert/strict`,
`node:module` and `node:fs/promises`, which existing tests already use):

- A: literal keys of `security.ts` `const fields` (regex `([A-Za-z]\w*):\s*\[` — spreads do not
  match), plus `OFFLINE_FIELDS` keys from `offline-security.ts`, plus `REVIEW_CONTROL_FIELDS` keys
  from `review-security.ts`.
- S: `case '(\w+)':` inside the slice from `switch(method) {` to `async function start()`.
- P: exposed key plus invoked method from `([A-Za-z]\w*):\([^)]*\)=>invoke\('(\w+)'` inside the
  `Object.freeze({...})` block. The two callback listeners do not match because their body is not
  `=>invoke(`.

Assertions:

1. `default:` arm throwing `Unsupported action` exists in the switch (R1 — the only assertion that
   fails before implementation).
2. `sorted(A) == sorted(S) == sorted(P)` (R2).
3. Every preload exposed key equals the action it invokes (R3).
4. Runtime probe: for every `method` in S, `validateRequest(method, {__probe:true})` must not throw
   with message `Unsupported action` (R5). Using a deliberately unknown key means the validator
   throws a parameter error (or `Invalid offline browsing request` /
   `Missing or unexpected review control fields`) while still proving allowlist membership, so no
   per-action valid parameter fixture is needed and the test stays compact.

R4 (unknown action rejected before any host runs) is already satisfied by `security.ts:49` and is
covered by existing suites (for example `loudness-host.test.mjs` asserts
`validateRequest('loudness.confirmation', ...)` throws); it is recorded here as a regression
contract, not as new work.

## No-assumption note: backend routing is not the parity target

Parity is defined over the three TypeScript files only. The Python core method registry is
deliberately excluded because UI actions and backend methods are not 1:1; `main.ts` reshapes,
merges and splits them:

- `prepSettings` → `prep.settings.get` with no parameters (dropped).
- `savePreferences` → `libraryHost.savePreferences(params)`, not `settings.update`.
- `listLibrary`/`getPrepCatalog` call `core.request` directly and enrich the response
  (`{...result, count: result.tracks.length}`).
- `renamePlaylist`/`duplicatePlaylist`/`openPlaylistEditor`/`openPlaylist` renumber `playlistId`
  with `Number(...)` before dispatch and reshape the response.
- `cancelCurrent` fans out to four different hosts plus an internal method-name filter.

Therefore no requirement, test, or guard may compare UI action names to Python method names.

## Decisions and alternatives

- **Chosen**: keep the switch, add a throwing `default:`. Minimal diff, no behavior change for
  existing paths, closes the silent `undefined` path.
- **Rejected (larger)**: derive the allowlist from a single exported dispatch table so the
  allowlist and dispatch cannot diverge. This is the real structural cure, but it moves ~60
  actions and the allowlist schema into new modules, far exceeding this work unit. It would also
  make `action()` importable and turn assertion 1 and 4 into a pure runtime test. Recorded as the
  candidate follow-up.
- **Rejected**: assert only `A ⊆ S`. It passes today and would miss a stale allowlist entry, which
  is exactly the direction that becomes fail-open without a `default:`.

## Safety considerations

- No audio mutation; no loudness, Serato, DSP, or Python change.
- No renderer, CSP, preload permission, or sandbox change.
- No new dependency and no `package.json`/lock change.
- No secret, credential, or user-data path is read or written by the test.
- Build output only: `npm run build` writes the gitignored `desktop-electron/.out/`; the CI wrapper
  writes the gitignored `.release-evidence/`. Neither is a source edit.
