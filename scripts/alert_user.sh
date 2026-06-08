#!/bin/bash
# Alert sound for user attention — 4 high-priority beeps at 3000 Hz
set -euo pipefail

BEEP="/tmp/beep.wav"

# Generate beep if missing
if [[ ! -f "$BEEP" ]]; then
    sox -n -r 44100 -c 1 "$BEEP" synth 0.2 sine 3000 vol 0.95
fi

# Play 4 times with short pause
for _ in 1 2 3 4; do
    afplay "$BEEP"
    sleep 0.15
done
