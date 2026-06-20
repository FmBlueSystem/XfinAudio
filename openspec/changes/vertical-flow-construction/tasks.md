# Tasks: Vertical flow construction foundation

- [x] Define the vertical workflow objective and boundaries.
- [x] Record proposal, spec, design, and state artifacts.
- [x] RED: add focused tests for the first application-level vertical workflow boundary.
- [x] GREEN: implement the smallest application boundary that coordinates existing recommendation/save collaborators.
- [x] REFACTOR: keep UI/controller code thin and move only orchestration that has test coverage.
- [x] VERIFY: run focused tests, then full XfinAudio gates for the recommend/save slice.
- [x] RED: extend the application boundary toward scan-to-recommend orchestration without desktop dependencies.
- [x] GREEN: compose scan/recommend through application collaborators while preserving UI worker ownership.
- [x] RED: extend the application boundary toward saved-playlist export orchestration without desktop-owned product policy.
- [x] GREEN: compose saved playlist export through application collaborators without changing export formats.
- [x] VERIFY: run full XfinAudio gates after each additional vertical-flow slice.
- [ ] Archive the OpenSpec change after scan/recommend/save/export coverage is implemented and verified.
