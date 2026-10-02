# Requirements

- GIVEN the hosted workflow, WHEN GitHub validates job-level configuration, THEN it does not reference the unavailable runner context in job-level environment values.
- GIVEN the Electron test step, WHEN it runs on the allocated machine, THEN XFIN_PYTHON identifies the same isolated hash-locked environment created earlier and every real-core integration remains enabled.
- GIVEN a corrected source commit, WHEN verification completes, THEN the full local aggregate and exact-head hosted checks must pass before a green/readiness claim; the earlier zero-job failure remains recorded.
