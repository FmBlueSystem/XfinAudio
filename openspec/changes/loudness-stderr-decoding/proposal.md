# Loudness stderr decoding
Native copy testing reproduced UnicodeDecodeError from FFmpeg metadata bytes,
although the process exited successfully with a valid ASCII loudness summary.
Scope: explicit tolerant stderr decoding, strict existing metric validation and
synthetic subprocess/cache-retry regressions. No audio, tags, Qt or metric-policy
changes. Existing cached failures require the existing force-reanalyze action.
Rollback: revert this bounded decoding slice if subprocess behavior regresses.
