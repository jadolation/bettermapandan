# Procurement Layout Fix Plan

## Current State
- `transparency.html` procurement section renders: 4 stat cards, 2 charts, table controls, table, pagination
- Search bar exists at `#procurement-search` inline with dup/CSV buttons
- Pagination exists with Prev/Next + page indicator
- `initProcurementTable()` in `assets/transparency.js` generates numbered pagination and renders rows
- Data is embedded correctly and charts/table are functional

## Issues to Fix
1. **Search bar layout** — The search input is inline with buttons using `flex-wrap: wrap`. On narrow viewports it wraps awkwardly. Needs a cleaner stacked or wrapped layout.
2. **Pagination visibility** — Numbered page buttons are injected by JS into `#procurement-pagination`, but the static HTML only shows Prev/Next + `1 / 1`. Need to ensure numbered buttons render and are styled consistently.
3. **Pagination functionality** — Prev/Next and numbered buttons must work with search/sort/dedupe state.

## Proposed Changes

### `build.py` — `generate_procurement()`
- Keep the controls row structure, but improve inline styles for better wrapping:
  - Make the right-side controls group wrap cleanly
  - Ensure search input has adequate width and doesn't collapse
- No structural HTML changes needed; JS handles numbered pagination injection

### `assets/transparency.js` — `initProcurementTable()`
- Ensure `renderPageNumbers()` output is inserted into `#procurement-pagination` correctly
- Add basic CSS class styling for pagination buttons so they look like clickable controls
- Ensure pagination click handler works for numbered buttons, Prev, and Next
- Ensure search input has a sensible min-width so it doesn't collapse to 0 on mobile

### `src/partials/base.html` or inline styles
- If needed, add minimal CSS for `.numbered-pages` button layout

## Validation
- Open `transparency.html`
- Verify search bar is visible and functional
- Verify numbered pagination buttons appear below/next to Prev/Next
- Verify clicking page numbers, Prev, Next all navigate correctly
- Verify search/sort/pagination interact correctly
- Verify layout looks clean on desktop and mobile widths
