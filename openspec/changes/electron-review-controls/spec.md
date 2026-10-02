# Scenarios
- GIVEN a generated review WHEN inspected THEN every transition component, explanation/warning and readiness check is visible with offline engine facts and no filesystem paths.
- GIVEN a current unprotected selection WHEN replacement comparison is requested THEN original engine results are compared without mutating the review.
- GIVEN a current review WHEN removal or exact-permutation reorder is applied THEN original engine helpers rescore it, required/protected controls remain enforced, readiness/quality are rebuilt and a fresh review identity supersedes prior save/export/Live contexts.
- GIVEN altered files/metadata/settings or an older identity WHEN an action is requested THEN it is rejected without publishing a mutation.
- GIVEN saved build controls WHEN restarted THEN only reauthorized available identities are restored, missing controls are counted honestly and not silently deleted.
- GIVEN explicit save of build controls WHEN revision and identities are valid THEN only app-owned build settings change, with no credentials or source audio touched; conflicts keep the current snapshot.
