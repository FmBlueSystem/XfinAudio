# Design

Keep the stdlib Nan transport seam. Validate endpoint shape without logging its
contents, require HTTPS, attach bearer credentials as an unredirected header, and
use an opener whose redirect handler refuses redirects. Tests replace HTTPS
handling with in-memory responses and fail any accidental network access.

Add one pure shared CSV text-cell encoder used only at CSV serialization edges:
playlist metadata, metadata-gap reports, and Serato/shared readiness reports.
Keep numeric columns outside that encoder and JSON serialization unchanged. Prefix
potential formula cells with an apostrophe before CSV quoting. Import as text for
spreadsheet workflows; preserve raw data through JSON.

No model/schema, audio-writing, configuration-default, or Serato crate behavior
changes. README (English/Spanish) and SECURITY disclose actual loudness behavior.
Full release gate belongs to the parent integration; this branch records focused
verification and explicitly leaves integrated completion pending.
