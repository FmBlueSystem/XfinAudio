# Design

Show Play while paused; route the same paused source to the existing player.play.
Accept Qt PlayingState from either loading or paused. Suppress intermediate table
selection restoration signals and publish only the final restored selection.

Direct population refreshes the existing active marker after cache invalidation,
then publishes final selection after replacing application records. Invalid-cache
same-path updates repaint; they never trigger an eager content rebuild.

Rescan direct population retains selected row positions, not original paths. A
changed order may therefore select a different track; final selection publication
then stops the prior preview. This slice does not promise path preservation across
rescan or redesign direct population. Sort restoration does preserve paths.
