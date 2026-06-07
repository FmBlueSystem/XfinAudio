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

### Manual gates still required

| Name | Status |
|------|--------|
| real Mixed In Key audio QA | pending_manual |

### Limitations

- Does not prove real Mixed In Key audio QA

**Note:** This non-audio evidence does not prove manual audio QA, clean macOS account validation, signing/notarization/DMG, or release completion.
