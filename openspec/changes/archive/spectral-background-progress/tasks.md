# Tasks: Spectral Background Progress Indicator

1. [x] **Proposal** — document intent, scope, risks, and success criteria.
2. [x] **Specification** — write GIVEN/WHEN/THEN scenarios for worker signal, AppState, and UI text.
3. [x] **Design** — choose status-line route and identify affected files.
4. [x] **TDD: SpectralCompletionWorker progress** — RED/GREEN/REFACTOR
   - [x] RED: add test proving `progress_updated` is emitted with correct counts.
   - [x] GREEN: implement `progress_updated` signal and emit counts from `_SpectralCompletionRunner`.
   - [x] REFACTOR: keep runner logic readable; count cached hits immediately.
5. [x] **TDD: AppState fields** — add `is_completing_spectral`, `spectral_progress_count`, `spectral_total_count`.
6. [x] **TDD: MainWindow wiring** — update AppState on `progress_updated` and clear on `finished`.
7. [x] **TDD: LibraryViewModel status text** — show spectral progress when active.
8. [x] **Verify** — run focused and full verification commands; produce `verify-report.md`.
9. [x] **Archive** — move change artifacts to `openspec/changes/archive/`.
