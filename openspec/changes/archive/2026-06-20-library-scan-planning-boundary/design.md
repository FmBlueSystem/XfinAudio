# Design: Library scan planning boundary

## Approach

Create `xfinaudio.library.scan_planning` for pure candidate selection:

- `SUPPORTED_AUDIO_EXTENSIONS` remains the shared extension set.
- `is_supported_audio_file(path)` owns suffix matching.
- `plan_supported_audio_paths(folder, list_paths)` filters supported paths, deduplicates by path string, and returns a deterministic list.

`scan_service.scan_folder()` will call the planner before metadata reads. `config.settings` will import supported extensions from the planning module rather than importing the full scan service.

## Safety

The change does not mutate audio, does not add DSP, does not write Serato DB V2 files, and does not change export formats. It only reduces duplicate scan work before existing metadata/audio execution.
