# HELP-3 Mixed In Key Metadata Contract Discovery

Date: 2026-06-03

## Scope

Inspected 10 local audio files that were reported as Mixed In Key processed. Inspection was metadata-only with `mutagen`; no audio files were saved or mutated. Large Serato/binary/base64 payloads are summarized only.

## Inspection harness

Script: `scripts/inspect_mik_tags.py`

- Uses `mutagen.File(path, easy=False)` for read-only metadata access.
- Never calls `save()` and does not open files for writing.
- Emits JSON summaries with file name, mutagen type, tag count, and safe representative values.
- Redacts GEOB binary data and truncates long Serato/base64 blobs.

## Files inspected

| # | File | Type | Key observations |
|---|---|---|---|
| 1 | `Give It All You Got (Mic by Jason Willmon) - full track from MIK.aif` | AIFF | `TBPM=128.550000`, `TIT2`, `TLEN`, Serato `GEOB` frames, playcount; no Camelot key or energy tag observed. |
| 2 | `Give It All You Got (Mic by Jason Willmon) - instrumental from MIK.aif` | AIFF | `TBPM=130.830000`, `TLEN`, Serato `GEOB` frames; no Camelot key or energy tag observed. |
| 3 | `It's Like That (DJ Edit) - full track from MIK.aif` | AIFF | `TBPM=129.100000`, `TIT2`, `TLEN`, Serato `GEOB` frames, playcount; no Camelot key or energy tag observed. |
| 4 | `It's Like That (DJ Edit) - instrumental from MIK.aif` | AIFF | `TBPM=129.100000`, `TIT2`, `TLEN`, Serato `GEOB` frames, playcount; no Camelot key or energy tag observed. |
| 5 | `It's Like That (DJ Edit) - acapella from MIK.aif` | AIFF | `TBPM=106.830000`, `TIT2`, `TLEN`, Serato `GEOB` frames, playcount; no Camelot key or energy tag observed. |
| 6 | `Give It All You Got (Mic by Jason Willmon) - acapella from MIK.aif` | AIFF | `TBPM=125.280000`, `TIT2`, `TLEN`, Serato `GEOB` frames, playcount; no Camelot key or energy tag observed. |
| 7 | `Change - A Lover's Holiday ... - 11B - Energy 7.flac` | FLAC | `bpm=116.000000`, `key` base64 JSON => `11B`, `energy` base64 JSON => `7`, `initialkey=Am`, `energylevel=7`, `grouping=7`, comment says `⚡️6`. |
| 8 | `Teena Marie - I Need Your Lovin' - 8A - Energy 6.flac` | FLAC | `bpm=107.670000`, `initialkey=8A`, `key` JSON => `8A`, `energy` JSON => `6`, `energylevel=6`, `grouping=6`, comment says `⚡️5`. |
| 9 | `Vanessa Williams - The Right Stuff.flac` | FLAC | `bpm=112.670000`, `initialkey=9A`, `key` JSON => `9A`, `energy` JSON => `6`, `energylevel=6`, `grouping=5`, title contains `Energy 6`. |
| 10 | `World's Famous Supreme Team - Hey DJ.flac` | FLAC | `bpm=94.890000`, lowercase variants `tbpm=95`, `tkey=9A`, `key` JSON => `9A`, `energy` JSON => `5`, `energylevel=5`, `grouping=4`, comment says `⚡️4`, publisher says `Energy 5`. |

## Representative raw tag keys

### AIFF / ID3-like tags

Observed keys: `TBPM`, `TIT2`, `TLEN`, `TXXX:Serato Analysis Flags`, `TXXX:SERATO_PLAYCOUNT`, `GEOB:Serato Autotags`, `GEOB:Serato BeatGrid`, `GEOB:Serato Overview`, `RVA2:SeratoGain`.

Representative values:

```text
TBPM => text ['128.550000']
TIT2 => text ['Give It All You Got (Mic by Jason Willmon) - full track from MIK']
TLEN => text ['325079']
GEOB:Serato Autotags / BeatGrid / Overview => binary Serato payloads, redacted
```

Contract impact: AIFF files in this sample can provide BPM and title, but not reliable Mixed In Key Camelot key or energy. These records should be marked incomplete for recommendation until key and energy are available from another accepted metadata source.

### FLAC / Vorbis comments

Observed candidate keys:

```text
bpm, tbpm, ibpm
key, initialkey, tkey
energy, energylevel, grouping, comment, publisher, title
artist, title, album, albumartist, genre, genre_category, subgenre, mood, dj_zone, danceability
serato_* fields, beatgrid, cuepoints, platinumnotes, replaygain_*
```

Representative Mixed In Key JSON payloads after base64 decode:

```json
{"algorithm":94,"key":"11B","source":"mixedinkey"}
{"algorithm":13,"energyLevel":7,"source":"mixedinkey"}
```

## Parser contract

Required normalized fields for a complete track:

- `bpm: float`
- `camelot_key: str` matching `1A..12A` or `1B..12B`
- `energy_level: int` from 1 to 10

Optional metadata:

- `title`
- `artist`
- `genre`
- `tags` from `genre`, `mood`, `subgenre`, `dj_zone`, and `genre_category`

### Field precedence

1. BPM: `bpm` > `tbpm` / `TBPM` > `ibpm`.
2. Camelot key: base64 JSON `key` with `source=mixedinkey` > `initialkey` if already Camelot > `tkey` if already Camelot > title Camelot fallback.
3. Energy: base64 JSON `energy` with `source=mixedinkey` and `energyLevel` > `energylevel` > `grouping` > `publisher` / `comment` textual fallback > title `Energy N` fallback.
4. Title: `title` > `TIT2`.
5. Artist: `artist` > `TPE1`.
6. Genre/tags: preserve `genre`; split comma-separated values from `genre`, `mood`, `subgenre`, `dj_zone`, and `genre_category` into de-duplicated tags.

### Observed variants and conflicts

- `initialkey` can be musical notation (`Am`) while Mixed In Key JSON `key` has Camelot (`11B`). Prefer JSON `key`.
- `grouping`, `comment` energy glyphs, and `energylevel` can disagree. Prefer JSON `energy`, then `energylevel`.
- Lowercase ID3-like FLAC variants exist (`tkey`, `tbpm`, `tlen`) and must be parsed case-insensitively.
- FLAC title and filename often include `- 8A - Energy 6`, but title/filename fallbacks are lower confidence than explicit tags.
- Serato `beatgrid`, `overview`, `markers`, and `autogain` payloads are large and not needed for HELP-3 parser completeness.

## Fixtures

Focused fixtures live at `tests/fixtures/mixedinkey_tag_variants.json`:

- `flac_mik_json_preferred`: JSON `key`/`energy` beats conflicting `initialkey` and comment.
- `flac_lowercase_variants_conflicting_energy`: lower-case variants and conflicting energy fallbacks.
- `aiff_id3_without_mik_key_energy`: AIFF has BPM/title but remains incomplete without key/energy.
- `flac_invalid_primary_bpm_uses_fallback`: invalid primary `bpm` falls through to `tbpm`.
- `flac_non_json_energy_uses_energylevel`: invalid/non-JSON `energy` falls through to `energylevel`.

## Non-goals for HELP-3

- No DSP, BPM/key detection, or beat tracking.
- No C++.
- No audio rendering or mutation.
- No UI.
- No recommendation scoring or exports.
- No full Serato/base64 fixture blobs.
