# Tasks

1. [x] Inspect existing packaged-runtime contract, disk, dependencies and official sources
2. [x] Write proposal/spec/design and explicit chained review plan
3. [x] RED: unit tests for source/gate binding, package layout, Qt/symlink rejection
4. [x] GREEN/REFACTOR: smallest assembly, frozen-core and pinned FFmpeg recipe
5. [ ] VERIFY: focused tests plus lint/format; synchronize only after V8 checkpoint
6. [ ] Run full exact-tree release aggregate without reduced coverage/omitted gates
7. [ ] Build only after exact-tree green gate and authorized build scope
8. [ ] Verify relocated Qt-free core + bundled FFmpeg against synthetic fixtures
9. [ ] Hand off package, source/provenance and verification artifacts without publishing

- [x] RED: reproduce untagged-WAV smoke failure; assert original scanner contract
- [x] GREEN: copy tagged synthetic input; provide preparation helper/instructions
- [ ] VERIFY: repeat exact-source aggregate, package seal and corrected smoke
