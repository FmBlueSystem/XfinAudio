# Hosted runner context correction

The first hosted run for published V13 failed workflow validation before creating any jobs. Source inspection found `runner.temp` in job-level `env`; GitHub's context availability table excludes `runner` there and permits it at step-level `env`. Move only the interpreter binding to the actual test step. Preserve all jobs, locked inputs, evidence, timeouts and test/coverage policy. No runtime or packaging change; source2.2.0 and previous artifacts remain distinct.
