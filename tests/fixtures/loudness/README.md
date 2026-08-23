# Synthetic loudness fixtures

`synthetic_tone_1khz.wav` is the committed 3-second source tone (SHA-256
`1cc3c200533b04ab502187521fe83c52e80632c0842e46ade33af899157f0430`). The
M4A fixtures are generated from it with the commands below, using the recorded
FFmpeg 8.0.1 fixture encoder (`ffmpeg -version` SHA-256
`7353334517ad3b7d889b9e7f5ff69c6ade10848dce703c2a66cd937f94c737e6`):

```bash
ffmpeg -y -hide_banner -loglevel error -i synthetic_tone_1khz.wav -c:a aac -profile:a aac_low -movflags +faststart synthetic_tone_1khz_aac.m4a
ffmpeg -y -hide_banner -loglevel error -i synthetic_tone_1khz.wav -c:a alac -movflags +faststart synthetic_tone_1khz_alac.m4a
```

- AAC-LC: `synthetic_tone_1khz_aac.m4a`, SHA-256 `3fd9dc58cdc6246c862ceb6499e8cb6a032c129802662e8f8af1cb65693c0cdb`
- ALAC: `synthetic_tone_1khz_alac.m4a`, SHA-256 `a4c3272c66e9d174200433a3355b6745dfa65984d596c0ac8ad0a8b08d79ad1f`

Both containers report exactly 3.000000 seconds. The frozen-path test prefers
`XFINAUDIO_FFMPEG_BINARY` for the rebuilt bundle candidate and otherwise uses a
compatible developer FFmpeg; it performs real decoding and never fakes metrics.
