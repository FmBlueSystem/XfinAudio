# Synthetic audio fixtures

The eight FLAC files were generated for automated tests. Each contains two seconds of stereo silence with synthetic title/artist/genre/BPM/key/energy tags. No user music is included. They test real metadata parsing, codec container validity, byte-range transport and playlist workflows. Silence cannot verify audible playback quality; native decoder/play/pause/seek checks remain required.
