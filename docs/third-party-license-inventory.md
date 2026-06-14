# Third-party dependency/license inventory

This inventory is generated from direct project dependency declarations and installed Python package metadata.
It is evidence for release readiness review, not legal clearance.

## Packages

| Name | Version | License metadata | Summary | Homepage / project URL | Legal review note |
|------|---------|------------------|---------|------------------------|-------------------|
| hatchling | Not provided in package metadata | Not provided in package metadata | Not provided in package metadata | Not provided in package metadata | Package was declared by the project but not found in installed distribution metadata. |
| mutagen | 1.47.0 | GPL-2.0-or-later | read and write audio tags for many formats | https://github.com/quodlibet/mutagen | — |
| pydantic | 2.13.4 | Not provided in package metadata | Data validation using Python type hints | https://github.com/pydantic/pydantic | — |
| pyinstaller | 6.20.0 | GPLv2-or-later with a special exception which allows to use PyInstaller to build and distribute non-free programs (including commercial ones) | PyInstaller bundles a Python application and all its dependencies into a single package. | https://pyinstaller.org | — |
| pyobjc-framework-Cocoa | 12.2 | MIT | Wrappers for the Cocoa frameworks on macOS | https://github.com/ronaldoussoren/pyobjc | — |
| pyright | 1.1.410 | MIT | Command line wrapper for pyright | https://github.com/RobertCraigie/pyright-python | — |
| PySide6 | 6.11.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Python bindings for the Qt cross-platform application and UI framework | https://pyside.org | PySide6/Qt licensing requires legal review before binary redistribution. |
| pytest | 9.0.3 | Not provided in package metadata | pytest: simple powerful testing with Python | https://docs.pytest.org/en/latest/ | — |
| pytest-cov | 7.1.0 | License :: OSI Approved :: MIT License | Pytest plugin for measuring coverage. | Not provided in package metadata | — |
| ruff | 0.15.15 | Not provided in package metadata | An extremely fast Python linter and code formatter, written in Rust. | https://docs.astral.sh/ruff | — |
| setproctitle | 1.3.7 | BSD-3-Clause | A Python module to customize the process title | https://github.com/dvarrazzo/py-setproctitle | — |

## Limitations and legal review gates

- XfinAudio source is GPL-3.0-only, but dependency metadata does not clear redistribution obligations.
- Package metadata may be incomplete, ambiguous, or different from the license terms that apply to redistribution.
- PySide6/Qt licensing requires legal review before binary redistribution.
- mutagen and other third-party dependencies require legal review before binary redistribution.
- No legal clearance or binary redistribution approval is implied by this inventory.

## Reproduce

```bash
uv run python scripts/third_party_license_inventory.py
uv run python scripts/third_party_license_inventory.py --format json --output /tmp/xfinaudio-third-party-inventory.json
```
