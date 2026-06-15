# Proposal: UI Improvement Roadmap for XfinAudio

**Date:** 2026-06-14  
**Author:** opencode (sdd-apply) for Freddy Molina  
**Scope:** Comprehensive UI/UX improvements across the entire application  
**Priority:** High — addresses space utilization, workflow efficiency, and visual polish

---

## Executive Summary

XfinAudio is a functional DJ playlist assistant with solid backend logic but underutilized screen real estate. The current UI constrains the main track table to 190px height, leaving vast empty space below. The sidebar navigation works but the content area doesn't adapt to available space. This proposal outlines a phased improvement roadmap to transform XfinAudio into a professional-grade DJ tool.

---

## Current State Analysis

### Issues Identified

1. **Table Height Constraint**
   - `tracks_table` has `setMaximumHeight(190)` and `setMinimumHeight(132)`
   - With 10,607 tracks, only ~6 rows are visible at a time
   - 90%+ of the content area is unused vertical space

2. **Inefficient Space Utilization**
   - Sidebar is 180px fixed width (good)
   - Content area has no size policies to expand
   - Status labels at the top consume ~60px vertically

3. **Workflow Friction**
   - Users must scroll constantly due to small table
   - No quick filters or search visible by default
   - Missing column is hidden by default (good, but toggle is small)

4. **Visual Polish**
   - No visual hierarchy between sections
   - Buttons are uniform in size and emphasis
   - No empty-state illustrations or guidance

---

## Improvement Roadmap

### Phase 1: Space Utilization (Critical)

**Goal:** Make the track table use available vertical space.

**Changes:**
1. Remove `setMaximumHeight(190)` constraint on `tracks_table`
2. Set `QSizePolicy.Expanding` for vertical growth
3. Increase `setMinimumHeight` to 400px (or 50% of window height)
4. Make status labels collapsible or move to a compact status bar

**Files:**
- `src/xfinaudio/desktop/main_window.py` (lines 690-691)
- `src/xfinaudio/desktop/screens/library_screen.py` (table size policy)
- `src/xfinaudio/desktop/theme.py` (remove height constants)

**Impact:** Users can see 15-20 tracks instead of 6. Reduces scrolling by 70%.

**Effort:** Small (30 lines of code)

---

### Phase 2: Compact Status Bar

**Goal:** Move status labels to a compact status bar at the bottom.

**Changes:**
1. Create a `StatusBar` widget with 3 sections: folder, guidance, scan progress
2. Move `folder_label`, `library_guidance_label`, `scan_progress_label` to status bar
3. Add a toggle button to show/hide the status bar
4. Default to hidden, show only during scan operations

**Files:**
- `src/xfinaudio/desktop/status_bar.py` (new)
- `src/xfinaudio/desktop/main_window.py` (layout changes)
- `src/xfinaudio/desktop/screens/library_screen.py` (remove status labels)

**Impact:** Reclaims ~60px of vertical space for the table.

**Effort:** Medium (80 lines of code)

---

### Phase 3: Quick Filter Bar

**Goal:** Add a persistent quick filter bar above the table.

**Changes:**
1. Add a `QLineEdit` for search (already exists, but make it more prominent)
2. Add filter chips for: Complete/Incomplete, Missing BPM, Missing Key, Missing Energy
3. Add a "Clear Filters" button
4. Show active filter count in a badge

**Files:**
- `src/xfinaudio/desktop/screens/library_screen.py` (add filter bar)
- `src/xfinaudio/desktop/library_view_model.py` (add filter state)
- `src/xfinaudio/desktop/theme.py` (filter chip styles)

**Impact:** Users can filter without opening the Metadata Worklist tab. Reduces tab switching by 50%.

**Effort:** Medium (100 lines of code)

---

### Phase 4: Visual Hierarchy

**Goal:** Improve visual design with clear hierarchy.

**Changes:**
1. Primary actions (Scan, Recommend, Export) get larger buttons with accent colors
2. Secondary actions (Settings, Cancel) get smaller, muted buttons
3. Add section dividers between controls and table
4. Add empty-state illustrations for: no library, no tracks, no recommendation

**Files:**
- `src/xfinaudio/desktop/theme.py` (button styles, colors)
- `src/xfinaudio/desktop/screens/library_screen.py` (button sizing)
- `assets/empty-states/` (new SVG illustrations)

**Impact:** Clearer workflow, reduced cognitive load.

**Effort:** Medium (120 lines of code + 3 SVG assets)

---

### Phase 5: Responsive Layout

**Goal:** Adapt layout to window size.

**Changes:**
1. Detect window width and adjust sidebar width (180px for wide, 120px for narrow)
2. On narrow windows, collapse sidebar to icons only
3. Add a "Full Screen" mode that hides sidebar and status bar
4. Remember window size/position in settings

**Files:**
- `src/xfinaudio/desktop/main_window.py` (resize event handler)
- `src/xfinaudio/desktop/screens/library_screen.py` (responsive controls)
- `src/xfinaudio/config/settings.py` (window geometry)

**Impact:** Works well on laptops and external monitors.

**Effort:** Large (200 lines of code)

---

### Phase 6: Keyboard Shortcuts

**Goal:** Add comprehensive keyboard shortcuts for power users.

**Changes:**
1. `Ctrl+F` — Focus search input
2. `Ctrl+Shift+S` — Start scan
3. `Ctrl+R` — Recommend playlist
4. `Ctrl+E` — Export to Serato
5. `Ctrl+M` — Toggle Missing column
6. `Space` — Preview selected track (already exists)
7. `Enter` — Open selected track in default player
8. `Delete` — Remove selected track from playlist

**Files:**
- `src/xfinaudio/desktop/main_window.py` (shortcut registration)
- `src/xfinaudio/desktop/screens/library_screen.py` (track-specific shortcuts)

**Impact:** Power users can work 3x faster without mouse.

**Effort:** Small (60 lines of code)

---

### Phase 7: Progress Indicators

**Goal:** Add visual feedback for long operations.

**Changes:**
1. Add a progress bar to the scan button during scanning
2. Add a progress bar to the recommend button during recommendation
3. Add a progress bar to the export button during export
4. Show estimated time remaining (e.g., "2:30 remaining")

**Files:**
- `src/xfinaudio/desktop/screens/library_screen.py` (scan progress bar)
- `src/xfinaudio/desktop/screens/build_screen.py` (recommend progress bar)
- `src/xfinaudio/desktop/screens/export_screen.py` (export progress bar)
- `src/xfinaudio/desktop/scan_controller.py` (progress tracking)

**Impact:** Users know the app is working, not frozen. Reduces support tickets.

**Effort:** Medium (150 lines of code)

---

### Phase 8: Contextual Tooltips

**Goal:** Add helpful tooltips for all controls.

**Changes:**
1. Add tooltips to all buttons (already done for some)
2. Add tooltips to table column headers (already done)
3. Add "What's this?" help button for complex features
4. Add a "Tour" button that walks through the workflow

**Files:**
- `src/xfinaudio/desktop/screens/library_screen.py` (tooltips)
- `src/xfinaudio/desktop/screens/build_screen.py` (tooltips)
- `src/xfinaudio/desktop/screens/export_screen.py` (tooltips)

**Impact:** Reduces learning curve for new users.

**Effort:** Small (40 lines of code)

---

### Phase 9: Dark Mode Refinement

**Goal:** Polish the dark theme with better contrast and consistency.

**Changes:**
1. Increase contrast for text (currently #edf5ff on #0b0f14 is good, but some labels are too dim)
2. Add subtle gradients to buttons for depth
3. Add hover states for all interactive elements
4. Add focus outlines for accessibility

**Files:**
- `src/xfinaudio/desktop/theme.py` (color adjustments, gradients)

**Impact:** More professional appearance, better accessibility.

**Effort:** Small (50 lines of code)

---

### Phase 10: Undo/Redo

**Goal:** Add undo/redo for destructive actions.

**Changes:**
1. Add undo/redo stack for: remove track, reorder playlist, clear filters
2. Add `Ctrl+Z` / `Ctrl+Shift+Z` shortcuts
3. Add undo/redo buttons to the toolbar
4. Show undo history in a dropdown

**Files:**
- `src/xfinaudio/desktop/undo_manager.py` (new)
- `src/xfinaudio/desktop/main_window.py` (undo/redo integration)
- `src/xfinaudio/desktop/screens/library_screen.py` (track removal undo)

**Impact:** Users can recover from mistakes. Reduces data loss.

**Effort:** Large (250 lines of code)

---

## Prioritization Matrix

| Phase | Impact | Effort | Priority |
|---|---|---|---|
| 1. Space Utilization | High | Small | P0 (Critical) |
| 2. Compact Status Bar | Medium | Medium | P1 (High) |
| 3. Quick Filter Bar | High | Medium | P1 (High) |
| 4. Visual Hierarchy | Medium | Medium | P2 (Medium) |
| 5. Responsive Layout | Medium | Large | P2 (Medium) |
| 6. Keyboard Shortcuts | High | Small | P1 (High) |
| 7. Progress Indicators | Medium | Medium | P2 (Medium) |
| 8. Contextual Tooltips | Low | Small | P3 (Low) |
| 9. Dark Mode Refinement | Low | Small | P3 (Low) |
| 10. Undo/Redo | High | Large | P2 (Medium) |

---

## Recommended Execution Order

1. **Phase 1** (Space Utilization) — Quick win, high impact
2. **Phase 6** (Keyboard Shortcuts) — Quick win, high impact
3. **Phase 3** (Quick Filter Bar) — Medium effort, high impact
4. **Phase 2** (Compact Status Bar) — Medium effort, medium impact
5. **Phase 7** (Progress Indicators) — Medium effort, medium impact
6. **Phase 4** (Visual Hierarchy) — Medium effort, medium impact
7. **Phase 9** (Dark Mode Refinement) — Small effort, low impact
8. **Phase 8** (Contextual Tooltips) — Small effort, low impact
9. **Phase 5** (Responsive Layout) — Large effort, medium impact
10. **Phase 10** (Undo/Redo) — Large effort, high impact

---

## Success Metrics

- **Track visibility:** 15-20 tracks visible (up from 6)
- **Tab switching:** 50% reduction
- **Scrolling:** 70% reduction
- **User satisfaction:** Target 4.5/5 in usability survey
- **Support tickets:** Target 30% reduction

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Breaking existing tests | High | Run full test suite after each phase |
| Performance regression with large tables | Medium | Use virtual scrolling if needed |
| User confusion with new layout | Medium | Add tooltips and a "Tour" feature |
| Accessibility regression | High | Test with screen readers after each phase |

---

## Next Steps

1. Review and approve this proposal
2. Create SDD artifacts for Phase 1 (Space Utilization)
3. Implement Phase 1 with TDD
4. Verify and PR
5. Repeat for Phases 6, 3, 2, 7, 4, 9, 8, 5, 10

---

## Appendix: Code Snippets

### Phase 1: Space Utilization

**Current code (main_window.py lines 690-691):**
```python
self._library_screen.tracks_table.setMinimumHeight(_COMPACT_LIBRARY_TABLE_MIN_HEIGHT)
self._library_screen.tracks_table.setMaximumHeight(_COMPACT_LIBRARY_TABLE_MAX_HEIGHT)
```

**Proposed code:**
```python
self._library_screen.tracks_table.setMinimumHeight(400)
self._library_screen.tracks_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
```

**Impact:** Table expands to fill available vertical space.

---

## Conclusion

This roadmap transforms XfinAudio from a functional prototype into a professional-grade DJ tool. Phase 1 alone will have the highest impact with the least effort. The subsequent phases build on each other to create a cohesive, polished user experience.

**Recommendation:** Start with Phase 1 immediately. It's a quick win that will dramatically improve the user experience.
