# Requirements

- GIVEN both hosted test jobs, WHEN test execution begins, THEN their required FFmpeg command is present and runnable; installation or probe failure stops the job.
- GIVEN a complete collected Python manifest, WHEN any selected test is skipped during setup or its test call, THEN the supported complete-execution gate fails instead of counting setup as execution.
- GIVEN every manifested test executes successfully, WHEN results are combined, THEN collection identity and coverage checks remain unchanged and the configured 89% floor remains authoritative.
- GIVEN the prior hosted result, WHEN reporting its evidence, THEN retain the actual 4,035-pass/21-skip outcome rather than relabeling it complete.
