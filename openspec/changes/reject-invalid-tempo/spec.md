# Requirements
- R1 GIVEN absent, nonfinite or nonpositive tag BPM WHEN parsed THEN BPM is unavailable and metadata incomplete; valid later candidates remain eligible.
- R2 GIVEN an invalid Mixed In Key beatgrid tempo WHEN parsed THEN valid flat tempo is used, or BPM stays missing.
- R3 GIVEN existing complete records carrying malformed BPM WHEN scored in either direction THEN return zero, an explanatory warning and no nonfinite component or axis.
- R4 GIVEN malformed or missing BPM in a recommendation WHEN readiness is evaluated THEN required metadata and BPM continuity block performance readiness.
- R5 GIVEN finite-positive numeric metadata in existing supported forms WHEN parsed THEN preserve two-decimal precision and existing source precedence, with no arbitrary maximum. Unsupported comma decimal notation remains unavailable.
