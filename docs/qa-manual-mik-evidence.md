# XfinAudio — Real Mixed In Key QA Evidence

- **Generated**: 2026-06-14T12:21:28.908285+00:00
- **Folder**: `/Volumes/dd/_Lossless/por_decada`
- **Git commit**: `9e51e53067ead3a59bafab4572ac2d2b5505ecee`

## Scan results

- Total supported tracks: 10392
- Complete metadata: 7210
- Incomplete metadata: 3182
- Cancelled: False

## Recommendations

### build
- Tracks recommended: 350
- DJ readiness: needs_review
- Warnings:
  - Excluded 3182 incomplete track(s)
  - Dropped 6860 generated track(s) because adjacent BPM jump exceeded 3.0%

### same_energy
- Tracks recommended: 39
- DJ readiness: needs_review
- Warnings:
  - Excluded 3182 incomplete track(s)
  - Filtered 6750 track(s) outside same_energy energy tolerance
  - Dropped 421 generated track(s) because adjacent BPM jump exceeded 3.0%

### peak_time
- Tracks recommended: 34
- DJ readiness: needs_review
- Warnings:
  - Excluded 3182 incomplete track(s)
  - Filtered 2818 track(s) outside peak_time energy range
  - Dropped 4358 generated track(s) because adjacent BPM jump exceeded 3.0%

### warmup
- Tracks recommended: 345
- DJ readiness: needs_review
- Warnings:
  - Excluded 3182 incomplete track(s)
  - Filtered 4392 track(s) outside warmup energy range
  - Dropped 2473 generated track(s) because adjacent BPM jump exceeded 3.0%

## Serato crate exports (temporary)

- build: 350 tracks, validated=True, crate=/var/folders/k2/vcwk4xx51gl9y8mxrd9mqjvh0000gn/T/xfinaudio-mik-qa-0devxae3/_Serato_/Subcrates/QA build.crate
- same_energy: 39 tracks, validated=True, crate=/var/folders/k2/vcwk4xx51gl9y8mxrd9mqjvh0000gn/T/xfinaudio-mik-qa-0devxae3/_Serato_/Subcrates/QA same_energy.crate
- peak_time: 34 tracks, validated=True, crate=/var/folders/k2/vcwk4xx51gl9y8mxrd9mqjvh0000gn/T/xfinaudio-mik-qa-0devxae3/_Serato_/Subcrates/QA peak_time.crate
- warmup: 345 tracks, validated=True, crate=/var/folders/k2/vcwk4xx51gl9y8mxrd9mqjvh0000gn/T/xfinaudio-mik-qa-0devxae3/_Serato_/Subcrates/QA warmup.crate

## Maintainer sign-off

- [x] I inspected the scan results and they match the source folder.
- [x] I inspected at least one generated Serato crate in a hex/text viewer.
- [x] I verified that no files were written outside the temporary evidence folder.
- [x] I confirm this evidence was generated against a real Mixed In Key processed library.

<!-- MIK-QA-STATUS: completed -->
