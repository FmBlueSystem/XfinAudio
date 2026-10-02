# Design

Mirror the existing public Homebrew FFmpeg prerequisite/probe into the legacy job before its aggregate. Keep workflow permissions, dependency locks, actions and job limits unchanged. Update the explicit batch plugin to track real, non-skipped test-call completion; do not let a setup event alone satisfy the execution manifest. Exercise setup and call skip cases with actual disposable pytest subprocesses. Retain complete collection and all other gate checks.
