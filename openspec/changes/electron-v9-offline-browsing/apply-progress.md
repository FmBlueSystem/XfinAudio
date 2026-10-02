# Apply progress

2026-10-01:
- Proposal/spec/design declared four chained review slices before production changes.
- RED: isolated Qt-free Python test collection failed for missing `headless.library_browse`; added adapters and atomic recovery storage; six tests GREEN. Additional duplicate/filter-order regression failed (Alpha v2 hidden by a nonmatching representative), then changed orchestration to match the original Qt filter-before-dedup pass; seven tests GREEN.
- RED: Node native-host/security tests failed missing modules; added strict request validation and main-owned native confirmation/drain; five tests GREEN.
- RED: renderer controller/view tests failed missing module; added provider-independent controls and stale-response protection; tests GREEN. Dynamic card/recovery controls resync after the app gate releases; dirty drafts veto deletion.
- RED: real app composition tests failed because controls were unmounted; shared-file owner integrated main/preload/security/model/app/index and both composition tests passed.
- Real Python bridge test exercises original filters/search/comparison, exact preview native confirmation, deletion, backend restart, recovery and exact ordered restore; original fixture audio hashes unchanged.
- Python backend shared-file owner composed BROWSE_FIELDS and SAVED_FIELDS with a separate strict dispatch RED/GREEN test.
- No audio/Serato/provider writes. Temporary test data only. No push/merge/tag/package/release from this slice.
