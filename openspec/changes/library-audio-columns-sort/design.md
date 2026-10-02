# Design
Mutagen already opens streams read-only. Capture recognized container/codec, positive finite bitrate/1000 and confirmed MP3 bitrate mode into reserved scanner values; propagate optional model fields, additive SQLite columns and safe headless DTO. Permit readable untagged streams (WAV/AIFF) to retain properties while their missing DJ metadata stays incomplete. Do not decode audio or use providers.

Headless Library query remains the single global sorter and whitelist validation stays strict. Add format/bitrate fields and a numeric Camelot key comparator; deterministic path tie-break uses internal identities without exposing paths. Missing data partition remains last regardless of descending.

Renderer uses the OfflineBrowseView applied state, shared with local controls. Header sort uses applied filters rather than unsaved draft edits. Track/title and artist become individually sortable Library columns; add format and declared bitrate columns. Keep review table behavior intact. Header sort controls obey the existing busy guard. No pagination exists in current Library; future paging must occur after global sort.

Metadata source nuance: declared bitrates are values provided by the parser, not whole-file-size estimates; ALAC header values can differ from encoded-stream averages. UI identifies the declared nature and MP3 VBR/ABR mode.

The schema upgrade is 6 → 7 and begins an explicit SQLite transaction, so DDL and user_version roll back together on interruption. Ordinary Library rescan refreshes properties even when file identity is unchanged. Import accepts exact known track definitions for versions 5, 6 and 7, compares by column name to allow append-only migrations, and reconstructs by verified named columns; unknown versions/columns/objects still fail closed.
