## Non-audio release gate evidence

**Overall status:** passed
**Mode:** run

### Automated gates

| Name | Status | Return code | Command |
|------|--------|-------------|---------|
| tests | passed | 0 | `uv run pytest -q` |
| lint | passed | 0 | `uv run ruff check .` |
| format | passed | 0 | `uv run ruff format --check .` |
| open-source publication docs | passed | 0 | `uv run pytest -q tests/test_open_source_license_docs.py tests/test_public_open_source_docs.py tests/test_github_community_templates.py tests/test_repository_publication_checklist.py tests/test_harmonic_mixing_doc.py` |
| publication artifact hygiene | passed | 0 | `uv run pytest -q tests/test_publication_artifact_hygiene.py` |
| source package hygiene | passed | 0 | `uv run python scripts/source_package_hygiene_check.py` |
| PyInstaller check-only | passed | 0 | `uv run python scripts/pyinstaller_build_smoke.py --check-only` |
| root artifact hygiene | passed | 0 | — |

### Test summary

- 593 passed

### Manual gates still required

| Name | Status |
|------|--------|
| real Mixed In Key audio QA | pending_manual |

Manual audio QA remains pending. Refer to the harmonic mixing guide and open-source publication docs for context.

### Limitations

- Does not prove real Mixed In Key audio QA
- This non-audio evidence does not prove manual audio QA, clean macOS account validation, signing/notarization/DMG, or release completion.

### Evidence generation

- Non-audio release gate runner: `scripts/release_gate_check.py`
- Use `--report-json PATH` to write structured evidence.
- Rendered with `scripts/render_release_gate_evidence.py`.
- CI uploads `non-audio-release-gate-evidence` artifacts.
- Source publication readiness refresh is tracked in the open-source release backlog.

### Third-party inventory

- third-party dependency/license inventory is available via `scripts/third_party_license_inventory.py` and documented in `docs/third-party-license-inventory.md`.
