# Requirements
- GIVEN disabled AI or missing credentials WHEN interpretation is requested THEN no transport runs and the existing configuration error is exposed.
- GIVEN paths embedded in requests or title/genre metadata WHEN a permitted request is built THEN known and recognizable paths are redacted while ordinary musical instructions remain.
- GIVEN Library language WHEN valid bounded JSON arrives THEN only validated visible filters with a known genre are returned; unknown metadata is never filled.
- GIVEN Editor language WHEN a supported operation arrives THEN a canonical local edit command is returned; arbitrary actions, paths, extra fields and invalid targets are rejected.
- GIVEN saved-set aggregates with temporary IDs WHEN retrieval/compare JSON arrives THEN only provided IDs are returned; comparisons require at least two sets and all descriptions/comparisons remain locally computed.
- GIVEN malformed, oversized, nonfinite, duplicate-key or unsupported model JSON WHEN parsed THEN bounded errors do not echo response content.
