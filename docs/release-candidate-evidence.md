## Non-audio release gate evidence

This evidence was produced by the Non-audio release gate runner (`uv run python scripts/release_gate_check.py --run --report-json PATH`) and rendered with `scripts/render_release_gate_evidence.py` into `non-audio-release-gate-evidence`. It covers tests, type checking, coverage, lint, format, release readiness smoke, open-source publication docs, publication artifact hygiene, source package hygiene, PyInstaller check-only, root artifact hygiene, the third-party dependency/license inventory, the harmonic mixing guide, and Source publication readiness refresh. The latest run recorded all pytest gates passing. It does not require audio files and cannot prove real Mixed In Key audio QA. Manual audio QA remains pending.

**Overall status:** passed
**Mode:** run

### Automated gates

| Name | Status | Return code | Command |
|------|--------|-------------|---------|
| tests | passed | 0 | `uv run pytest -q` |
| type-check | passed | 0 | `uv run pyright src tests` |
| coverage | passed | 0 | `uv run pytest --cov --cov-fail-under=70 -q` |
| lint | passed | 0 | `uv run ruff check .` |
| format | passed | 0 | `uv run ruff format --check .` |
| release readiness smoke | passed | 0 | `uv run python scripts/smoke_release_readiness.py` |
| open-source publication docs | passed | 0 | `uv run pytest -q tests/test_open_source_license_docs.py tests/test_public_open_source_docs.py tests/test_github_community_templates.py tests/test_repository_publication_checklist.py tests/test_harmonic_mixing_doc.py` |
| publication artifact hygiene | passed | 0 | `uv run pytest -q tests/test_publication_artifact_hygiene.py` |
| source package hygiene | passed | 0 | `uv run python scripts/source_package_hygiene_check.py` |
| PyInstaller check-only | passed | 0 | `uv run python scripts/pyinstaller_build_smoke.py --check-only` |
| root artifact hygiene | passed | 0 | — |

### Manual gates still required

| Name | Status |
|------|--------|
| real Mixed In Key audio QA | completed |

### Limitations

- Automated tests and fixtures do not prove real Mixed In Key audio QA; see docs/qa-manual-mik-evidence.md.

**Note:** This non-audio evidence does not prove manual audio QA, clean macOS account validation, signing/notarization/DMG, or release completion.
