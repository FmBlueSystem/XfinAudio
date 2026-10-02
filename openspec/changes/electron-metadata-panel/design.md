# Design

metadata.report is a parameter-free JSONL command composed from headless.metadata_report, exposed by a parameter-free allowlisted preload method. The host handles routing and integration. The renderer metadata.ts module builds a self-contained panel from typed report data and an opaque-ID preview callback, reusing existing CSS classes. No arbitrary path or file operation reaches the renderer.
