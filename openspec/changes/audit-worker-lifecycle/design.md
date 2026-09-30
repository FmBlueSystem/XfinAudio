# Design

Use ScanService current/replacement accessors matching RecommendationService;
publish copies before rendering and retain standalone-test compatibility.
LibraryWatchService catches startup OSError, clears lifecycle state, logs/emits an
actionable warning. Domain watcher startup cleans partial resources.
MainWindow has an idempotent asynchronous close phase: disable new UI work, request
service cancellation, retain ownership, poll for idle with a Qt timer and retry
close. No main-event-loop wait and no terminate. Service request ids suppress stale
results; owned thread collections cover replacements. Background analysis objects
remain retained until actual thread finish and do not start downstream stages on
shutdown. Existing scan cancellation tokens remain the cooperative boundary;
blocking third-party/AI work finishes under its existing timeout.
Subprocess tests use synthetic delays/local temporary databases, never real audio
or network. Parent integration runs the complete release gate after all slices.
