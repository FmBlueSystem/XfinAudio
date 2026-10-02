# Apply progress

2026-10-01: Proposal, specification, design and tasks complete. The approved scope includes these commands, automatic post-scan completion and original engine reuse. No production changes yet. Preparing RED tests for completion and preference behavior.

## Python completion and scoring slice

- RED: ten completion tests failed with absent command/module; GREEN: original adapters sequentially reused with bounded two-file batches, current-version/current-file cache filtering, status, cancellation and safe persistence failures.
- RED: eleven preference/scoring tests failed because cohesion was absent; GREEN: revision-bound original ScoringSettings.spectral_cohesion is preserved through Prep and Live. Existing metadata-only Live expectations now explicitly use the original configured 0.5 policy; old spectral test fixtures explicitly declare CURRENT_ANALYSIS_VERSION rather than obsolete default version 1.
- RED: two race tests reproduced stale source rebinding inside a repository update and acknowledged cancellation reporting cancelled:false; GREEN: original repository update methods accept optional expected_file_identity, and JSONL finalization normalizes late profile cancellation while holding its publication lock.
- Refactor: one shared current-profile filter protects both status and downstream original scoring. Adapter algorithms and profile/scoring formulas remain untouched. Unrelated scoring caller defaults remain 0.0; headless backend explicitly supplies persisted application policy.
- Runtime: librosa>=0.10,<0.12 added to the separate hash-locked headless requirements. Root pyproject/uv.lock already declare librosa, so neither changed and no root uv sync ran. New v9/.venv has no PySide6. pytest is installed there for verification only and is not added to runtime requirements.
- Dispatcher: combined independently tested Library/Saved and GeneratedReview/PrepSettings services under backend.py. Added read-only Serato source review verification as a safe blocker while preserving metadata selection and existing blocked-preview semantics.
