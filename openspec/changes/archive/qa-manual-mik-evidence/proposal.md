# Proposal: XfinAudio Real Mixed In Key QA Evidence and Fixture Pack

## Intent

Close the last manual release gate — `real Mixed In Key audio QA` — by combining:

1. A reproducible manual QA harness that the maintainer runs against a real MIK-processed folder.
2. A fixture pack of MIK-style metadata variants (and optionally short tagged audio clips) to harden automated tests.
3. Automated tests that exercise the scan/recommend/export pipeline against those fixtures.
4. A mechanism in `release_gate_check.py` that marks the gate as completed when evidence exists.

## Scope

### In Scope

- Create `scripts/manual_mik_qa_harness.py` to scan/recommend/export a real MIK folder and produce Markdown evidence.
- Create `docs/qa-manual-mik-evidence.md` checklist/template.
- Expand `tests/fixtures/` with MIK metadata variants for edge cases (conflicting energy, missing key, BPM fallback, etc.).
- Add tests that use the new fixtures.
- Update `scripts/release_gate_check.py` to check for `docs/qa-manual-mik-evidence.md` or a generated evidence file.

### Out of Scope

- Running the harness against the maintainer's private library (this agent cannot access it).
- DSP or audio analysis.
- Writing to live Serato libraries.

## Capabilities

- `qa-manual-mik-evidence`: Manual QA harness + evidence file.
- `mik-fixture-pack`: Deterministic fixtures for complete/incomplete/conflicting MIK metadata.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `scripts/` | Created | `manual_mik_qa_harness.py` and evidence rendering. |
| `tests/fixtures/` | Created | New MIK metadata/audio fixtures. |
| `tests/` | Modified | New tests using fixtures. |
| `scripts/release_gate_check.py` | Modified | Check for manual QA evidence. |
| `docs/` | Created | `qa-manual-mik-evidence.md` checklist. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Maintainer has no MIK folder available | Low | Document exact requirements; metadata-only fixtures still add value. |
| Harness is too slow on large libraries | Medium | Add cancellation/timeout and progress output. |
| Evidence file gets stale | Medium | Include timestamp and commit hash in evidence. |

## Success Criteria

- [ ] `uv run pytest -q` passes.
- [ ] `uv run pyright src tests` passes.
- [ ] `uv run pytest --cov --cov-fail-under=70 -q` passes.
- [ ] `uv run ruff check .` passes.
- [ ] `uv run ruff format --check .` passes.
- [ ] `uv run python scripts/release_gate_check.py --run` passes.
- [ ] `scripts/manual_mik_qa_harness.py` exists and can generate evidence.
- [ ] New fixtures cover complete, incomplete, conflicting-energy, and BPM-fallback cases.
- [ ] `release_gate_check.py` reports the manual gate status based on evidence presence.
