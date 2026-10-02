# Self-contained Linux Electron bundle

Deliver a relocatable Linux x86_64 folder/tarball containing Electron 44.5.1,
the compiled local UI, frozen Python headless core, and FFmpeg. End users do not
install Python, pip, npm, Qt, or FFmpeg. Existing operating-system desktop/glibc
libraries remain prerequisites and the tested platform is explicitly recorded.
No macOS installer, signing, release publication, DSP additions, provider calls,
original-audio processing, or live Serato writes are in scope.

Risks: hidden Python imports, accidental Qt collection, FFmpeg format coverage,
old glibc compatibility, and packaging stale/unverified sources. Builds fail
closed on invalid gate evidence, source digest mismatch, or Qt artifacts.
Rollback: discard the separate output folder; source and application data remain intact.

Review chain (explicit chained-PR plan; no monolithic review):
1. Source sealing, complete-gate/environment validation and their strict tests
2. Relocatable assembly/freeze/bootstrap and focused safety/relocation tests
3. FFmpeg source/flags/toolchain locks and license/provenance records (generated
   lock material reviewed separately from behavior-changing code)
4. Synthetic relocated runtime smoke and the final full aggregate evidence

Each behavioral slice targets fewer than 400 changed implementation/test lines;
the complete lock and accumulated SDD evidence remain attached to their slice.
All slices must be green together before the application artifact is built.
