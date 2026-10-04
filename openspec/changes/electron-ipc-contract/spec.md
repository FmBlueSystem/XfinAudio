# Observable requirements

No implementation details. Every scenario is falsifiable by a test that runs against the built
Electron sources and the compiled `security.js`.

Set A is the action set accepted by `validateRequest`, set S is the set of `case` labels in the
`action()` dispatch switch, and set P is the set of action names exposed on `window.xfin` by the
preload bridge. Subscription helpers (`onLibraryStatus`, `onProgress`) are channels, not actions,
and are outside A, S and P.

## R1 — Unhandled allowlisted action fails closed

- GIVEN an action name that `validateRequest` accepts
- WHEN that name has no `case` in the `action()` dispatch switch
- THEN the call rejects with an error instead of resolving `undefined`.
  Today no such name exists, so this is verified structurally: the switch must end in a `default`
  arm that throws `Unsupported action` (`main.ts:109-181` has none today → observable failure).

## R2 — Three-way action parity

- GIVEN the allowlist accepted by `validateRequest`
- AND the dispatch cases in `action()`
- AND the actions exposed by the preload bridge
- WHEN all three are enumerated
- THEN the three sets are equal (A = S = P).
  Today all three contain the same 60 actions, so this requirement is a regression guard; it must
  fail if any one side gains or loses an action. It is falsifiable in both directions: a key added
  to `OFFLINE_FIELDS`/`REVIEW_CONTROL_FIELDS`/the literal fields without a switch case fails, and
  a new `case` or a new `invoke(...)` without a matching allowlist key fails.

## R3 — Bridge keys name the action they dispatch

- GIVEN an action exposed on `window.xfin`
- WHEN its implementation calls `ipcRenderer.invoke`
- THEN the exposed key equals the dispatched action string (for example `xfin.listLibrary()`
  invokes `listLibrary`, never a different or aliased action).

## R4 — Unknown actions are rejected before any host runs

- GIVEN an action name that is neither in A nor in S
- WHEN the IPC handler receives it
- THEN it is rejected with `Unsupported action` (`security.ts:49`) before any host, dialog,
  Python core call, or `libraryHost`/`serato`/`loudness`/`optionalAi`/`offline`/`profiles` work
  begins.

## R5 — Allowlisted actions are recognized by the validator

- GIVEN any action in S
- WHEN `validateRequest` is called with that action and a parameter object containing an
  unknown key
- THEN it throws a parameter error, never `Unsupported action`.
  This is the runtime half of R2: it proves the allowlist is the *effective* allowlist, including
  the keys supplied through the `OFFLINE_FIELDS` and `REVIEW_CONTROL_FIELDS` spreads.

## R6 — No behavior or surface change

- GIVEN the change is applied
- WHEN the Electron suite runs
- THEN no argument schema, no error message for existing paths, and no user-facing control has
  changed; only `undefined`-resolution on an unhandled allowlisted action becomes a rejection.
