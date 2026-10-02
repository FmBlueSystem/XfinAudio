# Design
Keep the text subprocess contract and explicitly use UTF-8 with replacement for
invalid byte sequences. Replacement preserves ASCII summary delimiters without
joining corrupted numeric tokens as errors=ignore could. Parsing remains strict.
No analysis-version bump: numerical semantics and valid caches are unchanged.
