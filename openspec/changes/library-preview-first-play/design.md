# Design

The controller populates rows directly and invalidates the screen cache. Library
state sync is lightweight. set_playing_row currently responds to the invalid cache
with a destructive full render while handling the playback signal. Selection
restoration briefly emits an empty selection, which stops the player.

Playback paint must use current table paths regardless of cache validity. Keep the
content cache invalid so a later explicit content render can reconcile rows/sort.
