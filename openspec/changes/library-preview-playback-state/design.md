# Design

Show Play while paused; route the same paused source to the existing player.play.
Accept Qt PlayingState from either loading or paused. Suppress intermediate table
selection restoration signals and publish only the final restored selection.
