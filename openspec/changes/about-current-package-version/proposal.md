# About: current package version
The owner requested a consolidated version update. Manifest and lock are 2.1.0,
but About still reports 1.0. Resolve the installed distribution version and ship
its metadata in the frozen bundle; do not hardcode another duplicate version.
Scope: About text, translation catalogs, packaging metadata and regression tests.
No release, tag, provider call or functional playlist change. Roll back this slice
if metadata resolution regresses; unavailable metadata must display Unknown.
