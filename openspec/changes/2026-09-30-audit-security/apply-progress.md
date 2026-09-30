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
