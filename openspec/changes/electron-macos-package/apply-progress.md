# Apply progress

Based on verified V10 archive/source seal. Cache and dependency RED failures recorded before implementation. Additional RED cases cover absolute install IDs, helper executable contexts and parenthesized otool descriptors. Mac-only implementation and 20 focused tests green; Ruff green. Frozen dependency probe cold/warm all six tagged formats passed, with 223 native objects audited, no Qt/network, actual cache loads and unchanged source hashes/mtimes. Electron distribution has 13 native objects audited. No final application build. Review chain: cache/entry/probe/tests; dependencies/audit/tests; recipe/locks/README/tests. Owner V11 integration and aggregate pending.

## Cross-platform integration review

The legacy full-gate environment uses Numba 0.65.1 while the locked standalone
runtime uses 0.68.0. A focused regression initially failed because the test
assumed only the newer hash stamp. The test now compares the unchanged inherited
base invalidation in both environments, still explicitly verifying executable
SHA256 whenever the original uses content hashes. Both environments must pass
focused checks; the pinned native cold/warm probe retains its hash assertion.
No locator or application behavior changed for this test correction.

Review also identified that final ad-hoc signing follows the embedded native
inventories. Those inventories must be labeled pre-signing, then a separate
external final-byte inventory must be produced after signing and signature
verification. This preserves signed-bundle integrity and avoids self-reference.
A failing regression and complete final-source gates are required for the fix.

The added cache test now also proves it restores the complete process environment
after its context. A preceding RED exposed untracked PATH mutation; tracking PATH
with the other hostile environment inputs fixes test isolation without changing
runtime code. This is separate from the unchanged legacy Qt MainWindow thread
connection deadlock observed during the first complete aggregate attempt. The
complete supported gate is repeated with smaller whole-file batches, retaining
every test, fresh coverage evidence and the unchanged configured floor.

## V12 packaged-mode correction

The native V11 app passed strict signing and frozen-core checks but retained the
stock Electron main executable name. Actual original and relocated launches showed
app.isPackaged false, selecting the development Python path. Two regression checks
failed before the fix: assembly identity and final-manifest renamed-path lookup.
The builder now renames the copied main executable, sets matching CFBundleExecutable
and updates every output native-audit path before signing. Original Electron/Python
application source is unchanged. No environment-variable packaged-mode override is
used. The official Electron 44.5.1 App::IsPackaged implementation confirms the
main-process executable-name check:
https://github.com/electron/electron/blob/v44.5.1/shell/browser/api/electron_api_app.cc

Full exact-source gates and an actual native packaged-mode/relocation test remain
required before this corrected bundle is accepted. The earlier frozen-core proof
does not imply that its GUI was functional.
