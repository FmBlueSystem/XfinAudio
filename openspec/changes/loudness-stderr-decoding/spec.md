# Requirements
- Valid ASCII summaries survive unrelated malformed UTF-8 metadata bytes.
- Corrupted numeric/units output remains unmeasurable, never repaired by dropping bytes.
- Nonzero exits remain unmeasurable; timeout/cancellation semantics are unchanged.
- Forced retry of a cached failure remeasures successfully with a synthetic transport.
- No real audio, tag writes, credentials, remote calls or native Qt changes in tests.
