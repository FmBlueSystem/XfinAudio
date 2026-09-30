# Design notes before Apply

## G1/G2
Base on integrated lifecycle commits 471f05d / 38e4e47: QObject controller under MainWindow; QThread parented under it; WorkerRegistry.retain(thread, worker); request IDs suppress cancelled/superseded results; MainWindow asynchronous close drains child QThreads. Add state via model_copy transitions, compatible with the parent's immutable-state work.

Capture selected controls, strategy, count, genre, settings and scanned-record snapshot on the GUI thread. Ensure candidate selection consumes the snapshot rather than current widget/window state. Use default-inert optional progress/cancellation callbacks at existing preparation stage boundaries, with no optimizer/scoring changes. Keep last result in state until successful current completion. Guard direct/keyboard entry points as well as buttons.

Domain cancellation checks occur before and after bounded candidate/variant stages. Do not claim immediate interruption inside a non-cooperative stage. Closing requests interruption and rejects publication; existing owner retains worker wrappers until destruction.

## H1
Reuse the existing deterministic transition data and score tooltip explanations rather than inventing an AI summary. Selection updates a read-only text area in normal tab order. Include from/to context, human warning summary and selected score detail. Preserve selection on unchanged render and clear old details after clear/replacement. Use compact-height constraints and test 1000x700 after generation/application.

## I1
Source inspection: SeratoRecommendationExportMixin._plan_current_serato_export resolves the discovered/explicit Serato library; safe_export_folder currently only changes readiness sidecars. Do not change writer semantics through a cosmetic CTA. Parent to choose accurate existing-destination guidance versus a separately specified staged-export change.
