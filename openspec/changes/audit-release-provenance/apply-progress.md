# Apply progress
2026-09-30: Read governance/audit and inspected current packaging, gate runner,
FFmpeg builder, tests, workflows, and release docs. Created isolated branch
`fix/release-build-provenance` from `0f2725ed459625f56d98ebb65493222ee5df11a5`.
Proposal/spec/design/tasks complete. No test or production edits yet.
Blocked pending parent confirmation of preceding correctness-tranche gate.

16:17 UTC: Parent explicitly authorized isolated Apply. Preceding integration gate
finished with 2748 passed / 5 failed; parent and algorithm owner retain those
regressions and final integrated verification. This is permission to proceed,
not a claim that the preceding gate was green.

Helper RED: 27 failing fixture assertions because the required enforcement
helper was absent (captured outside the repository). GREEN: all 27 helper tests
pass after implementation, including dirty source, changed SHA/version/content,
missing/malformed evidence, permission/link mutation, unsafe links/special files,
and root-artifact output refusal. Refactored with Ruff; focused checks green.

Shell RED (prior preserved log): 10 failures, 7 passes before orchestration changes.
Recovery on 2026-09-30: offscreen alone did not resolve the packaging test abort;
the fake QApplication test needed the shared qapp fixture for its real QIcon.
The separate check-only failure was an unset virtualenv PATH, not product behavior.
GREEN: 69 provenance/shell/packaging tests passed with the shared virtualenv on
PATH and offscreen Qt. Tests include gate failure, dirty/changed source, failed
build/smoke, tampered/stale reuse, and optional signing/notary failure propagation.
No native macOS tools were run: the shell fixture uses synthetic executables.

Supply-chain RED: three failures demonstrate mutable workflow tags and an extra
unused signature download. GREEN: 40 action-pin, FFmpeg, and workflow tests pass
with all eight workflow action references on the reviewed official SHAs and only
the checksum-verified FFmpeg archive downloaded. The checksum mismatch rejection
and safe extraction tests remain green; no compiler/network download ran.

VERIFY: 154 focused tests passed across provenance/shell/packaging (69), action
pins/FFmpeg/workflows (40), and release/publication/docs gates (45). Whole-tree
Ruff lint/format passed (354 Python files); Pyright src/tests and both release
helpers passed with zero errors/warnings; Bash syntax and Git whitespace checks
passed. The shared virtualenv, offscreen Qt, and writable temporary caches were
used; no dependencies or native release artifacts were installed/built.
The isolated aggregate gate was stopped at the parent's request (exit 130),
after it showed failures on the older base. It is NOT a successful gate. The
parent owns the final aggregate gate on the integrated committed exact HEAD.
