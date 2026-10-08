# Observable requirements

Behavior-only statements for the review remediation. Implementation detail lives in
`design.md`; the finding identifiers match `proposal.md`.

- **R1 — A playlist export stays inside the export folder.**
  GIVEN an export request whose name is absolute, contains separators, contains `..`, or
  resolves outside the chosen export folder,
  WHEN the app writes the export,
  THEN the name is reduced to a single path component or the request is rejected with an
  error, and no file is written outside the export folder.

- **R2 — A staged AI request cannot change while its paid call is in flight.**
  GIVEN an authorized AI request that has been sent and is awaiting a response,
  WHEN renderer input, a preview refresh or a draft edit tries to replace the staged
  request text,
  THEN the in-flight request keeps the exact text and binding it was authorized with, the
  late result is still applied to that binding, and the user sees local-hold feedback
  explaining why the field is not editable.

- **R3 — The headless dependency snapshot matches the lockfile.**
  GIVEN `uv.lock` and `desktop-electron/requirements-headless.txt`,
  WHEN the snapshot is compared with the lock,
  THEN every snapshot pin is hash-locked, matches the locked version, and the snapshot
  contains no distribution that the lock does not resolve; the packaging build inputs
  consume the snapshot instead of keeping a second edited copy.

- **R4 — Shipped documents describe the tree that exists.**
  GIVEN any tracked document outside the historical evidence folders,
  WHEN it references a repository path, runs `uv run <target>`, or names a UI control,
  THEN the path exists, the target is either a declared console script or a tool this
  project depends on, and the named control appears in the surface that ships it,
  AND a document that describes the removed Qt tree declares itself historical in its
  opening lines, and each architecture note names `4e31a3a`.

- **R5 — A discarded failure is observable.**
  GIVEN a track profile that cannot be deserialized, or an audio file whose MD5 signature
  cannot be read,
  WHEN the scan continues past it,
  THEN the scan still succeeds and the track is still reported as not analysed, and a
  warning naming the track and the cause is logged at `WARNING` level, so the condition is
  distinguishable from a track that was never scanned.

- **R6 — The SDD configuration and skill describe the live stack.**
  GIVEN `openspec/config.yaml` and the `gentle-ai-sdd-tdd` skill,
  WHEN they are compared with `pyproject.toml`, `uv.lock` and the gate script,
  THEN every declared dependency exists in the lock, the interpreter floor matches, no Qt
  package is declared, and the verification section defers the coverage floor to
  `pyproject.toml` instead of naming a `--cov-fail-under` value.

- **R7 — No Qt-era artifact ships, runs or is documented as current.**
  GIVEN the shipped package, the CI workflows and the user documents,
  WHEN Qt residue is looked for,
  THEN no Qt Linguist catalog is force-included or present, no workflow sets
  `QT_QPA_PLATFORM`, no module exposes the retired Qt connection-dialog API, the probe
  text is defined exactly once, and the AI settings document names only controls the
  Electron panel ships.

- **R8 — The improvement save bridge is exercised against the real core.**
  GIVEN the Electron renderer's `playlist.edit.save_improvement` path with a Python
  interpreter available,
  WHEN the improvement flow runs end to end through the real bridge,
  THEN the core computes the proposal identifier and draft digest, the renderer's exact
  save payload persists the improved order to disk, a stale digest, an unknown proposal
  identifier and a non-matching draft are each rejected without persisting anything, and
  no draft identifier or library path appears in the outbound provider body.
