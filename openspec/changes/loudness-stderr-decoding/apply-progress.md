# Progress
Real synthetic subprocess reproduction: 6 failed / 2 passed before the patch.
Popen now explicitly decodes UTF-8 with replacement; only two production lines
changed. Strict parser, lifecycle, duration policy and cache version are unchanged.
A real temporary repository regression confirms cached transient failure requires
force_reanalyze, then the valid summary replaces it without reading/writing audio.
