# Design: Multi-Software DJ Export

## Architecture

Three new exporter modules live alongside the existing Serato exporter under `xfinaudio.exporting`. Each exporter is a deterministic text/XML builder with a `build_*` pure function and a `write_*` file helper.

```
xfinaudio/exporting/
├── __init__.py
├── explainability.py
├── playlist_exporters.py
├── serato_crate.py
├── serato_playlist_exporter.py
├── rekordbox_xml.py       # NEW
├── traktor_nml.py         # NEW
└── virtualdj_xml.py       # NEW
```

## Components

### Exporters

| Module | Build Function | Write Function | Output |
|--------|---------------|----------------|--------|
| `rekordbox_xml` | `build_rekordbox_playlist_xml` | `write_rekordbox_playlist_xml` | `.xml` |
| `traktor_nml` | `build_traktor_playlist_nml` | `write_traktor_playlist_nml` | `.nml` |
| `virtualdj_xml` | `build_virtualdj_playlist_xml` | `write_virtualdj_playlist_xml` | `.xml` |

### ExportScreen Changes

- Add `QComboBox software_selector` with items `[Serato, Rekordbox, Traktor, VirtualDJ]`.
- Emit `software_changed(str)` signal when selection changes.
- Update `preview_button` and `export_button` text dynamically.
- Keep `objectName("seratoExportButton")` for stylesheet compatibility.

### MainWindow Routing

- `_selected_export_software() -> str`: reads combo box.
- `preview_export(...)`: dispatches to `preview_serato_export` for Serato, else shows a generic preview with target path.
- `export_recommendation(...)`: dispatches to the correct writer based on selected software.
- `export_recommendation_to_serato(...)` remains unchanged for backward compatibility.

## Testing Strategy

- Exporter tests parse generated XML with `xml.etree.ElementTree` and assert structure/attributes.
- ExportScreen tests verify combo options, signal emission, and button label updates.
- MainWindow integration test verifies Rekordbox routing writes an XML file.

## Error Handling

- Exporters raise standard exceptions on I/O errors; `MainWindow.export_recommendation` catches and logs them.
- Validation errors (no recommendation, blocked readiness, missing safe folder) are surfaced via `status_label`.
