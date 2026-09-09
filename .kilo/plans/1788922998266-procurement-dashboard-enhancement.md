# Procurement Dashboard Enhancement Plan

## Goal
Match the BetterGov procurement dashboard UI exactly: stat cards, charts, searchable/sortable/paginated table with CSV export, duplicate removal, and org count — all fully functional client-side.

## Current State (post-initial implementation)
- `extract_procurement.py` already has `_clean()` and `procurement.json` regenerated.
- `build.py` `generate_procurement()` renders 4 stat cards, charts, search input, sortable headers, prev/next pagination, CSV button, and embeds `PROCUREMENT_CONTRACTS`.
- `transparency.js` has chart rendering and `initProcurementTable()` for search/sort/pagination/CSV.
- Built `transparency.html` contains the procurement section and all data attributes.
- **Known broken behaviors:**
  1. `initProcurementTable()` is gated behind `if (typeof Chart !== "undefined")` — table interactivity silently fails if Chart isn't loaded first.
  2. Pagination only shows Prev/Next — no numbered page links like `1 2 3 4 ... 11`.
  3. "Remove duplicate contracts" button exists but has no handler.
  4. No "1 orgs" unique-organization indicator.
  5. Table renders 20 static server rows; JS replaces them, but initial render gap can show stale data.
  6. Procurement section placement needs to be directly below the transparency hero.

## Target UI (from reference)
- 4 stat cards: Unique Categories, Total Value, Average Cost, Total Contracts
- Monthly Cost Trend line chart + Top 10 Awardees horizontal bar
- Controls row: "211 results | ₱438,912,506 | 1 orgs" | Remove duplicate contracts | CSV
- Full-width table with 9 columns and sortable headers
- Pagination: `Showing 1-20 of 211` + `1 2 3 4 ... 11` numbered links
- All features functional client-side

## Required Changes

### 1. `assets/transparency.js`
- **Remove the Chart gate:** `initProcurementTable()` must run unconditionally on `DOMContentLoaded`, independent of Chart.
- **Start with empty table body:** Server should render empty `<tbody></tbody>`; `initProcurementTable()` populates it entirely client-side from `window.PROCUREMENT_CONTRACTS`. This avoids stale 20-row flashes.
- **Numbered pagination:** Generate page number links dynamically (e.g., `1 2 3 4 ... 11`) with ellipsis for large page counts. Keep Prev/Next.
- **Duplicate removal:** Add a "Remove duplicate contracts" toggle button. Deduplicate by normalized `title + awardee + amount` (case-insensitive, trim). When active, filter `PROCUREMENT_CONTRACTS` and re-render. Toggle button state visually.
- **Org count indicator:** In the results header, show unique organization count: e.g., `1 org` or `5 orgs`. Compute from currently filtered contracts.
- **Showing text:** Update `Showing X-Y of Z` based on filtered + paginated results.
- **CSV export:** Keep existing `downloadCSV("procurement")` behavior — generates real CSV from `window.PROCUREMENT_CONTRACTS`.
- **Sort visual state:** Add `.sort-asc` / `.sort-desc` class to active `<th>` so user sees direction.

### 2. `build.py` → `generate_procurement()`
- Render empty `<tbody></tbody>` instead of 20 static rows.
- Add `data-column` attributes to all sortable `<th>` elements.
- Add `id="procurement-search"`, `id="procurement-csv-btn"`, `id="procurement-page-info"`, `id="procurement-pagination"`, `id="procurement-page-indicator"`.
- Keep `window.PROCUREMENT_DATA` and `window.PROCUREMENT_CONTRACTS` embeds.
- Keep single attribution footer: `Source: PhilGEPS | Aggregated via: BetterGov.ph | License: ...`.
- Locale strings already in place.

### 3. `src/pages/transparency.html`
- Move the procurement section so it appears immediately below the transparency hero (top of page content), before appropriations/revenue/fiscal sections.
- Ensure no duplicate procurement markup exists.

### 4. `locales/en.json` and `locales/fil.json`
- Verify `search_placeholder`, `sort_by`, `showing_page_x_of_y`, `download_csv`, `remove_duplicates` are present (already added in prior step).
- No new keys needed.

## Execution Order
1. Update `build.py` `generate_procurement()`: empty `<tbody>`, ensure all required IDs/data-columns.
2. Rewrite `assets/transparency.js`: unconditional table init, numbered pagination, duplicate toggle, org count, sort indicators.
3. Update `src/pages/transparency.html`: move procurement section below hero.
4. Rebuild with `.venv/bin/python build.py` and validate.

## Validation Criteria
- Open `transparency.html` and verify:
  - 4 stat cards render with correct values.
  - Monthly trend + top 10 awardees charts render.
  - Table body starts empty, then fills with 20 rows via JS.
  - Search input filters rows in real time.
  - Clicking column headers sorts asc/desc with visual indicator.
  - Pagination shows numbered links `1 2 3 4 ... 11` and updates "Showing X-Y of Z".
  - "Remove duplicate contracts" toggles deduplicated view.
  - Results header shows `X orgs` count.
  - CSV button downloads `mapandan-procurement.csv`.
  - Single attribution footer, no duplicates.
  - Procurement section appears directly below hero.
