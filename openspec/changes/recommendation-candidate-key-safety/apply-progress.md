# Apply Progress: Recommendation candidate key safety

## 2026-06-20

- Created SDD artifacts for the recommendation candidate key safety slice.
- RED: added `tests/test_recommendation_presenter.py::test_build_pool_treats_invalid_candidate_camelot_key_as_incompatible`; focused run failed with `ValueError` from `_camelot_compatible()` on `bad-key`.
- GREEN: added safe Camelot parsing in `candidate_pool` so invalid keys are treated as incompatible/unknown.
- Focused evidence: `uv run pytest tests/test_recommendation_presenter.py -q` passed (`8 passed`), and scoped pyright passed (`0 errors`).
