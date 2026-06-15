# Verify Report: Auto-save Playlist on Export

## Verification commands

| Command | Result |
|---|---|
| `uv run pytest tests/test_export_coordinator.py tests/test_playlist_coordinator.py tests/test_main_window.py -q` | PASS — 110 passed |
| `uv run pytest -q` | PASS — 813 passed, 4 warnings |
| `uv run pyright src tests` | PASS — 0 errors |
| `uv run pytest --cov --cov-fail-under=70 -q` | PASS — 813 passed, coverage 88.52% |
| `uv run ruff check .` | PASS |
| `uv run ruff format --check .` | PASS — 185 files already formatted |
| `uv run python scripts/release_gate_check.py --run` | PASS |

## Notes

- No audio files were mutated.
- No DSP scope was added.
- Release gate warnings were existing librosa/audioread warnings from fixture-based integration tests.
