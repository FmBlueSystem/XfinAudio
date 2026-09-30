# Observable requirements

- R1: GIVEN an enabled/keyed AI client WHEN its endpoint is HTTP, malformed,
  credential-bearing, or contains controls THEN fail before invoking transport,
  without echoing the endpoint or key. Valid custom HTTPS endpoints still work.
- R2: GIVEN a credential-bearing request WHEN any 301/302/303/307/308 response
  redirects to the same origin, another host/port, or HTTP THEN fail without a
  second request. The original non-redirected HTTPS call retains authorization.
- R3: GIVEN formula-like text beginning with =, +, -, @ (including leading
  whitespace/control variants) WHEN any shared CSV report is exported THEN
  prefix that cell with an apostrophe. Ordinary text and numeric fields retain
  their existing representation; commas, quotes, and line breaks remain valid CSV.
- R4: GIVEN the same metadata WHEN exported as JSON THEN all raw values survive
  unchanged, including formula-like strings.
- R5: GIVEN a reader of security/README documentation THEN the default-enabled
  loudness setting clearly gates both analysis and automatic file tag writing,
  including replacement of existing comments; no separate write switch is claimed.
