# Requirements
- GIVEN installed package metadata WHEN About opens THEN it shows that version.
- GIVEN unavailable metadata WHEN About opens THEN it shows Unknown, not 1.0.
- GIVEN a frozen build WHEN data are collected THEN package metadata is included.
- GIVEN Spanish UI WHEN About opens THEN the version label is translated.
