# Apply progress

RED: three-click preview retained the pause icon; the resumed callback remained
PAUSED; sorting stopped playback; removing the playing row left stale selection.
GREEN: same-source paused preview resumes without stop/load; state callback accepts
PAUSED; table rebuild blocks restoration signals and publishes final selection once.
The render extras reflect the playing path after that final selection is handled.
All shell probes use a non-playing fake QObject player and synthetic paths.
