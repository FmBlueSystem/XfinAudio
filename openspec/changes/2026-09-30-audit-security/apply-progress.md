# Apply progress

- Read repository governance and SDD/TDD skill before changes.
- Proposal/spec/design/tasks complete before production implementation.
- Updated scope to exclude other DJ software and S3 per owner direction.
- S1 RED pending; no production implementation yet.

## S1 transport slice
- RED: new offline security tests produced 26 failures / 10 passes before code.
  Insecure endpoints reached transport; 301/302/303 followed redirects; credentials
  were stored in redirect-copyable headers. 307/308 POST already failed safely.
- GREEN: require valid credential-free HTTPS endpoints; reject all redirects;
  attach Authorization only as an unredirected header.
- REFACTOR: keep injectable transport and stdlib TLS behavior; format/lint pass.
- VERIFY: 95 Nan tests pass; focused pyright reports 0 errors.

## S2 CSV slice
- RED: shared export regressions produced 32 failures / 8 passes before code.
- GREEN: one pure text encoder now protects playlist, metadata-gap, and readiness
  CSV text; numeric columns and every JSON path retain existing values.
- REFACTOR: helper isolates Unicode whitespace/control/format detection; ordinary
  commas, quotes, CR/LF, existing apostrophes, and control-only text stay intact.
- VERIFY: 78 focused tests pass; focused lint/format/type checks pass.
- Documented import-as-text convention and unperformed manual spreadsheet check.
