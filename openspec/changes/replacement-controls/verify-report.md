# Verification
- Focused: `pytest -q tests/test_replacement_controls.py tests/test_dj_controls.py
  tests/test_playlist_service.py`: 247 passed, including 10 replacement checks.
- Changed Python files: Ruff lint/format and Pyright with the existing virtualenv
  interpreter passed (0 errors). `git diff --check` passed.
- Requirements: direct/desktop original exclusions, current exclusions, previous
  removals, genre metadata/backfill, original start/manual anchor, current lock
  exception, explicit anchor removal, and conflicting current exclusion verified.
- `uv run python scripts/release_gate_check.py --run` started with isolated HOME
  and writable UV cache. Full/integrated gate remains pending; focused success
  does not establish full-suite or release readiness. Integration owner will run
  the exact combined commit gate and record its final outcome.
- No real audio/Serato mutations, push, PR, deployment, or build artifacts.
