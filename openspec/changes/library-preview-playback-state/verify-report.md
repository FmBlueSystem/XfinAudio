# Focused verification

Four new failing regressions were observed before changing production code.
88 focused tests passed across lifecycle, Library preview/screen/path index and
player state-machine tests. Targeted Ruff lint/format and Pyright passed using
the project virtual environment for installed dependencies.

The first-Play preservation regression remains green. Sort may intentionally
replace table items, but no transient empty selection stops the surviving preview.
Removing the selected path publishes empty selection and stops it deliberately.

Broader Linux lifecycle and aggregate verification remain integration work.
This focused slice uses synthetic fixtures and does not establish native GUI acceptance.

## Extended Linux lifecycle verification

The expanded focused selection passed 125 tests before the final two-branch rescan
parameterization; the final 15-case lifecycle module and targeted types/lint passed
again afterward. The repeat test exercises 20 play/pause/resume/stop cycles.
Same-path rescans preserve playback and repaint Pause; removed paths stop. Reorder
keeps the selected row index, so the selected path may change: both branches assert
PLAYING if the original path remains selected, otherwise IDLE. This is truthful
selection synchronization, not a new promise of path-preserving rescan behavior.
Navigation/state sync retains item identities; intentional rescan/sort rebuilds are
explicit in the tests. Close stops the fake player and destruction cancels a queued
callback scoped to that QObject. Late PlayingState after stop does not restart it.

A separate Linux QMediaPlayer probe used a generated muted WAV: first Play,
advancing position, Pause, resume, Stop and close passed; item/selection identities
and the synthetic file were unchanged. No output audio device was available.
This establishes backend state/decoding behavior only; audible output and native
GUI acceptance remain separate validation requirements.

Aggregate verification must run on the final integrated candidate before native
trial. No complete project gate is claimed by this focused slice.
