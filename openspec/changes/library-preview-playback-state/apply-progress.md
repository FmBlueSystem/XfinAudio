# Apply progress

RED: three-click preview retained the pause icon; the resumed callback remained
PAUSED; sorting stopped playback; removing the playing row left stale selection.
GREEN: same-source paused preview resumes without stop/load; state callback accepts
PAUSED; table rebuild blocks restoration signals and publishes final selection once.
The render extras reflect the playing path after that final selection is handled.
All shell probes use a non-playing fake QObject player and synthetic paths.

Extended RED found a rescan still playing with a Play glyph, and a reordered
rescan whose visible selected path disagreed with the controller. Repaint on
invalid-cache population and publish final direct-population selection.
Linux lifecycle coverage now includes navigation, same/removed/reordered rescans,
search, sort, quick filters, source switching, 20 cycles and callback teardown.
