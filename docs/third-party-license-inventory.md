# Third-party dependency/license inventory

XfinAudio keeps a reproducible dependency/license inventory for GPL-3.0-only open-source release readiness review. The inventory records package metadata evidence; it does not grant legal clearance.

## Quick path

```bash
uv run python scripts/third_party_license_inventory.py
uv run python scripts/third_party_license_inventory.py --format json --output /tmp/xfinaudio-third-party-inventory.json
```

The default command renders Markdown to stdout. Use `--format json` for machine-readable evidence and `--output PATH` to write a file outside project-root `build/` or `dist/`.

## What the inventory includes

| Field | Source |
|-------|--------|
| Package name | Direct runtime, dev, and build dependencies declared in `pyproject.toml`. |
| Version | Installed distribution metadata via `importlib.metadata`. |
| License metadata | `License` field when present, otherwise license classifiers when present. |
| Summary | Installed package `Summary` metadata when present. |
| Homepage / project URL | `Home-page` or selected `Project-URL` metadata when present. |
| Legal review note | Evidence-based warning notes, especially for PySide6/Qt, mutagen, and binary redistribution. |

## Project license context

XfinAudio source is distributed as a full open-source project under GPL-3.0-only. Redistribution must comply with GPLv3 and all third-party dependency obligations.

## Limitations and legal review gate

- Package metadata may be incomplete, ambiguous, stale, or different from redistribution terms.
- PySide6/Qt licensing requires legal review before binary redistribution.
- mutagen and other third-party dependencies require legal review before binary redistribution.
- No legal clearance or binary redistribution approval is implied by this inventory.
- The script does not run web research, inspect vendored license files, or create release artifacts.

## Current status

Inventory tooling is available at `scripts/third_party_license_inventory.py` and covered by tests. Legal review remains pending before binary or app bundle redistribution.
