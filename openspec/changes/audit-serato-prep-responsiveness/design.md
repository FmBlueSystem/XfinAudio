# Design notes before Apply

## G1/G2
Base on integrated lifecycle commits 471f05d / 38e4e47: QObject controller under MainWindow; QThread parented under it; WorkerRegistry.retain(thread, worker); request IDs suppress cancelled/superseded results; MainWindow asynchronous close drains child QThreads. Add state via model_copy transitions, compatible with the parent's immutable-state work.

Capture selected controls, strategy, count, genre, settings and scanned-record snapshot on the GUI thread. Ensure candidate selection consumes the snapshot rather than current widget/window state. Use default-inert optional progress/cancellation callbacks at existing preparation stage boundaries, with no optimizer/scoring changes. Keep last result in state until successful current completion. Guard direct/keyboard entry points as well as buttons.

Domain cancellation checks occur before and after bounded candidate/variant stages. Do not claim immediate interruption inside a non-cooperative stage. Closing requests interruption and rejects publication; existing owner retains worker wrappers until destruction.

## H1
Reuse the existing deterministic transition data and score tooltip explanations rather than inventing an AI summary. Selection updates a read-only text area in normal tab order. Include from/to context, human warning summary and selected score detail. Preserve selection on unchanged render and clear old details after clear/replacement. Use compact-height constraints and test 1000x700 after generation/application.

## I1
Source inspection: SeratoRecommendationExportMixin._plan_current_serato_export resolves the discovered/explicit Serato library; safe_export_folder currently only changes readiness sidecars. Do not change writer semantics through a cosmetic CTA. Parent to choose accurate existing-destination guidance versus a separately specified staged-export change.

### I1 alternatives prepared, neither applied
- Preserve direct Serato: preview the resolved full Subcrates path and track count before confirming the write; identify whether an existing crate is replaced and where its backup lives. Label the configurable folder as reports-only. Keep metadata-worklist destination explicit too.
- Stage artifacts: use the selected safe output root for crate bytes and reports, but keep track-path encoding tied to the intended Serato audio volume/library. Do not derive audio-relative paths from the staging directory. Preview output and later manual-copy instructions; avoid selecting or mutating a live library as a side effect.
- Both alternatives need explicit recovery tests before claiming durability: atomic replacement, validation failure, preexisting backup, write failure and rollback. Current direct writer only copies an existing target to a fixed .bak, writes bytes directly, and returns a readback-equality flag. Generated names avoid collisions at planning time; concurrent writers are not established safe.

### I1 decision resolved before Apply
The user confirmed direct Serato export, with no separate staging folder. The integrated hardened writer is owned by the integration branch (1a7fab3); this slice corrects UI destination guidance and optional report-folder labels, adds preview report/backup context, and discloses automatic loudness tag/comment writes in Settings. It does not change writer or default-enabled loudness semantics. Translation source and supported compiled catalogs receive the new critical copy.
