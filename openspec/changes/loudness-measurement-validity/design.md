# Design and evidence

Retain the existing TOO_SHORT partial status; preserve available integrated LUFS and true peak. The existing all-three complete predicate prevents tag writes. Qualify the selected-track display. Advance analysis/tag schema to v2 so startup-artifact results are not revived from old cache or metadata. Reject nonfinite model/parser values and negative LRA.

EBU Tech 3341 (2023), section 2.4, p6, states that during the first 60 s of LRA measurement the meter shall indicate that LRA is not yet considered stable. This is an EBU-mode stability-indication requirement, not a requirement to discard LUFS or true peak and not proof that every 60 s signal is stable. We conservatively omit LRA from complete persisted comments during that interval.

Sources: https://tech.ebu.ch/docs/tech/tech3341.pdf ; https://tech.ebu.ch/docs/tech/tech3342.pdf ; https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1770-5-202311-I!!PDF-E.pdf ; https://ffmpeg.org/ffmpeg-filters.html#ebur128

Linux FFmpeg 7.1.5 was measured independently. The packaged macOS 7.1.1 binary remains unvalidated. Mono uses native channel weighting, not dual-mono compensation.

Duration is the scanner-supplied metadata duration. NaN/infinity/negative duration cannot yield a complete profile; unknown zero remains partial. This patch does not add a decoded-duration parser. Stale metadata duration can still misstate duration and is a documented boundary. Finite integrated values at the -70 LUFS print floor are rejected conservatively because the summary does not distinguish gated-out material there.
