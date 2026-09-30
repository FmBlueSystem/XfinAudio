# Verification

## Result
The local release-hardening slices pass their focused verification. The final
integrated exact-HEAD non-audio gate remains pending and parent-owned. No release,
push, merge, deployment, real app build, signing, or notarization was performed.

## Requirement evidence
- R1: synthetic shell tests reject dirty source, gate failure, source edits or
  new commits during gate/build; fresh and reused apps execute the gate first.
- R2: helper tests reject stale/malformed evidence, SHA/version/content/mode/link
  changes, external/broken links, and special files; shell tests reject bad reuse
  before execution/signing and validate a fresh build and its reuse. The staged
  bundle is verified against the sidecar before image creation.
- R3: both workflows require all eight reviewed immutable action references;
  FFmpeg downloads only the hash-verified archive. Checksum mismatch still blocks
  tool execution; extraction safeguards remain tested.
- R4: synthetic signing/notary success and failure propagation tests pass,
  including refusal of notarization without a signing identity.

## Commands and outcomes
Using the shared pinned virtualenv on PATH and QT_QPA_PLATFORM=offscreen:
- Provenance helper, DMG shell, PyInstaller packaging tests: 69 passed.
- Immutable action pins, FFmpeg, and both workflow suites: 40 passed.
- Publication/license/community/docs/hygiene and release-gate tests: 45 passed.
- Pyright src/tests plus release_provenance.py and build_ffmpeg_universal.py:
  0 errors, 0 warnings, 0 informations.
- Ruff check .: passed; Ruff format --check .: 354 files already formatted.
- bash -n scripts/build_dmg.sh and git diff --check: passed.
- Aggregate release gate: interrupted on parent request (exit 130), not passed;
  the isolated older base was already reporting unrelated integration failures.
  Parent must rerun the full gate on the final integrated committed HEAD.

RED evidence was preserved before the helper and shell changes. Recovery also
captured the isolated Qt abort; requesting qapp fixes that test's real QIcon use.
Supply-chain RED captured three failures before action pin/download changes.
Diagnostic logs stay outside the repository's root build/dist directories.

## Native verification limits
Linux fixtures exercise control flow and local integrity, not real macOS
PyInstaller/codesign/spctl/hdiutil behavior, notarization, Gatekeeper acceptance,
clean-account startup, real audio/Serato QA, or legal redistribution clearance.
The sidecar is local process evidence, not signed attestation or reproducible
build proof; dependencies, toolchains and ignored FFmpeg inputs are not attested.
