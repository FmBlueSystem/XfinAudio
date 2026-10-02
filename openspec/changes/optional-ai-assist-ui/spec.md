# Requirements
- Given default controls, when typing or using offline actions, then no AI request occurs.
- Given AI enabled and per-surface disclosure accepted, when Ask AI is clicked, then captured minimal inputs are interpreted off the UI thread.
- Given cancellation, replacement context, changed request, revoked consent or retry, when old work completes, then it cannot alter the current UI.
- Library shows editable interpreted filters; Editor only previews a local validated command; saved-set results reference captured IDs and render local evidence.
- Configuration and transport failures provide actionable safe messages. Configure AI opens existing Settings. Window shutdown retains all running workers.
- Given current Metadata gaps or a ready Live session, when consent and Ask AI are explicit, then only aggregate gaps or opaque candidate metrics are sent. Commentary is labeled generated and read-only, is cleared on context change, and never mutates tags, rank, order or playback.
