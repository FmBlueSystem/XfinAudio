# Design

Keep all V12 application source and runtime recipes unchanged. Version changes touch only Python/Node project metadata and corresponding lock entries. Root/current Electron entry documentation points to the migration scope and source-candidate notes; historical validation is retained with clear chronology.

Retain the existing read-only GitHub Actions permissions and public pinned actions. CI uses the legacy locked environment for the retained complete Python suite and a separately hash-locked Qt-free environment for actual Electron subprocess tests. The existing sharded runner continues owning collection completeness, coverage combination and configured floor. A bounded result verifier may enforce Node no-skip success without fixing the count. No provider credentials, user data or downloaded private fixtures enter CI.

Do not modify the existing watcher implementation or any file in its five-file delta. Publication source manifests exclude development environments, generated builds, runtime binaries, credentials and user data. Review inventory is content-derived. Dependency inventory is provenance evidence, not a compatibility/legal opinion.
