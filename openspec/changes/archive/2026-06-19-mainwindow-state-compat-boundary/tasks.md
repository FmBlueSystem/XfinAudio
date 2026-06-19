# Tasks: MainWindow State Compatibility Boundary

- [x] 1. RED: add focused tests proving shell compatibility owns legacy state writes.
- [x] 2. GREEN: add shell compatibility state-write helper and delegate `MainWindow.__setattr__` to it.
- [x] 3. REFACTOR: keep naming and exports small, with no broad shell rewrite.
- [x] 4. VERIFY: run focused tests, main-window tests, type/lint/format, release gate.
