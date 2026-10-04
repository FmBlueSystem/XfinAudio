# Verification

Slice 1 was documentation-only; slice 2 below applied the module and tests as commit
`3fabf88`. No real artifact exists, so the real-build gates (real `.app`/DMG/
`hdiutil`/`codesign`/notarization) were not run; the synthetic fake runner proves no
real app, DMG or signing call is made.

## Behavior slice (applied) — `3fabf88`

- RED: `uv run pytest tests/test_macos_dmg.py -q` -> 15 failed on
  `FileNotFoundError: .../dmg.py`; a second RED covered two safety defects (streaming
  digest, partial-evidence cleanup); GREEN followed.
- `uv run pytest tests/test_macos_dmg.py tests/test_macos_recipe.py -q` -> 28 passed.
- `uv run ruff check`, `uv run ruff format --check`, `uv run pyright` on the two
  changed files -> clean.
- Canonical `uv run python scripts/release_gate_check.py --run` -> exit 0: 4205 pytest
  passed, 94.45% coverage (floor 89), pyright 0, ruff/smoke/source hygiene green.
- The synthetic runner proves rejection + checksum paths only; notice presence is not
  legal clearance.

Not claimed by this slice: a built `.app` or DMG, a clean-account open, Gatekeeper
approval, notarization, signing, redistribution clearance, or a clean-host QA result.
No full delivery or clean-account QA was performed; the real build requires the
owner's exact V11 seal and authorization, and Developer ID is unavailable.
Notices presence is a build-embedding check, not legal clearance.
