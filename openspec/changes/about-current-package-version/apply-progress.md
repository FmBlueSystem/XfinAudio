# Progress
Three initial regressions failed against the stale About/spec implementation.
Metadata-based version resolution, frozen metadata inclusion and compiled catalog
updates then passed. A fourth real-QTranslator regression exposed the existing
host-context mismatch; the two version messages now use MainWindow, matching
the actual host. No unrelated menu translations were changed.
