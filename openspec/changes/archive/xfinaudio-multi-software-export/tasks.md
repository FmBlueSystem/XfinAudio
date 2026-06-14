# Tasks: XfinAudio Multi-Software DJ Export

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 800-1200 |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 exporters → PR 2 ExportScreen selector → PR 3 MainWindow routing → PR 4 QA evidence |
| Delivery strategy | auto-chain |
| Chain strategy | feature-branch-chain |

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Rekordbox/Traktor/VirtualDJ exporters | PR 1 | Pure text/XML builders |
| 2 | ExportScreen software selector | PR 2 | QComboBox + dynamic labels |
| 3 | MainWindow routing | PR 3 | Dispatch to selected exporter |
| 4 | QA evidence | PR 4 | Tests, verify report |

---

## Unit 1: Exporters

### 1.1 RED: Add Rekordbox exporter tests

- [x] 1.1.1 Create `tests/test_rekordbox_exporter.py`
- [x] 1.1.2 Test XML root, collection, track locations, playlist node
- [x] 1.1.3 Test XML escaping of special characters
- [x] 1.1.4 Run and confirm failures

### 1.2 GREEN: Create Rekordbox exporter

- [x] 1.2.1 Create `src/xfinaudio/exporting/rekordbox_xml.py`
- [x] 1.2.2 Implement `build_rekordbox_playlist_xml` and `write_rekordbox_playlist_xml`

### 1.3 RED: Add Traktor exporter tests

- [x] 1.3.1 Create `tests/test_traktor_exporter.py`
- [x] 1.3.2 Test NML root, collection, location, tempo, playlist node
- [x] 1.3.3 Run and confirm failures

### 1.4 GREEN: Create Traktor exporter

- [x] 1.4.1 Create `src/xfinaudio/exporting/traktor_nml.py`
- [x] 1.4.2 Implement `build_traktor_playlist_nml` and `write_traktor_playlist_nml`

### 1.5 RED: Add VirtualDJ exporter tests

- [x] 1.5.1 Create `tests/test_virtualdj_exporter.py`
- [x] 1.5.2 Test VirtualFolder root, song entries, absolute paths
- [x] 1.5.3 Run and confirm failures

### 1.6 GREEN: Create VirtualDJ exporter

- [x] 1.6.1 Create `src/xfinaudio/exporting/virtualdj_xml.py`
- [x] 1.6.2 Implement `build_virtualdj_playlist_xml` and `write_virtualdj_playlist_xml`

---

## Unit 2: ExportScreen Selector

### 2.1 RED: Add ExportScreen tests

- [x] 2.1.1 Create `tests/test_export_screen_software_selector.py`
- [x] 2.1.2 Test selector has four options
- [x] 2.1.3 Test software_changed signal
- [x] 2.1.4 Test button labels update
- [x] 2.1.5 Run and confirm failures

### 2.2 GREEN: Add selector to ExportScreen

- [x] 2.2.1 Add `QComboBox software_selector`
- [x] 2.2.2 Populate with Serato, Rekordbox, Traktor, VirtualDJ
- [x] 2.2.3 Emit `software_changed` signal
- [x] 2.2.4 Update button labels dynamically

### 2.3 REFACTOR

- [x] 2.3.1 Preserve `objectName("seratoExportButton")` for stylesheet compatibility

---

## Unit 3: MainWindow Routing

### 3.1 RED: Add MainWindow integration tests

- [x] 3.1.1 Create `tests/test_main_window_multi_software_export.py`
- [x] 3.1.2 Test selector exists in MainWindow
- [x] 3.1.3 Test export button reflects selected software
- [x] 3.1.4 Test Rekordbox export writes XML file
- [x] 3.1.5 Run and confirm failures

### 3.2 GREEN: Wire routing in MainWindow

- [x] 3.2.1 Import new exporter write functions
- [x] 3.2.2 Add `_selected_export_software()` helper
- [x] 3.2.3 Add `export_recommendation()` dispatcher
- [x] 3.2.4 Add `preview_export()` dispatcher
- [x] 3.2.5 Connect ExportScreen signals to new dispatchers

### 3.3 REFACTOR

- [x] 3.3.1 Keep `export_recommendation_to_serato` for backward compatibility
- [x] 3.3.2 Keep Serato-specific guards (readiness blocked, no recommendation)

---

## Unit 4: QA Evidence

### 4.1 Automated gates

- [x] 4.1.1 Run `uv run pytest -q` → **734 passed, 0 failed**
- [x] 4.1.2 Run `uv run ruff check .` → New files clean
- [x] 4.1.3 Run `uv run ruff format --check .` → Clean

### 4.2 Verify report

- [x] 4.2.1 Create `verify-report.md`
