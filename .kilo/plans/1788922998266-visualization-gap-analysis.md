# Visualization Gap Analysis — Better Mapandan

## 1. Current State

- **Index (`index.html`)**: Hero banner with static statistics counter.
- **About (`about.html`)**: Textual history; no data visualizations.
- **Government (`government.html`)**: Organizational chart image; no dynamic data.
- **Legislative (`legislative.html`)**: Table listing of ordinances/issuances; no charts.
- **Services (`services.html`)**: Service directory cards; no usage or popularity metrics.
- **Statistics (`statistics.html`)**: Population trend chart (line); no barangay-level breakdown.
- **Transparency (`transparency.html`)**: Budget table; no category breakdown or trends.
- **Search (`search.html`)**: Text search results; no analytics or faceted counts.

## 2. Data Sources Available

| Source | Format | Notes |
|--------|--------|-------|
| `legislative.json` | JSON | Ordinances + executive issuances, no author field |
| `budget.json` | JSON | Annual budget line items |
| `services.json` | JSON | Service descriptions |
| `population.csv` | CSV | Barangay-level population data |
| PhilGEPS API | REST | Live procurement data |
| Weather API | REST | Current conditions + forecast |

## 3. Gaps to Fill

### High Priority

1. **Legislative Charts**
   - **Goal**: Show ordinance/issuance volume per year and by category.
   - **Files to modify**: `legislative.html`, `js/main.js`.
   - **Implementation**: Create `renderLegislativeChart()` using Chart.js; load `legislative.json` and aggregate counts by `year` and `type`.

2. **Procurement Category Breakdown**
   - **Goal**: Visualize spend distribution by category from PhilGEPS data.
   - **Files to modify**: `transparency.html`, `js/philgeps.js` (new).
   - **Implementation**: Fetch PhilGEPS data, group by `category`, render doughnut chart.

3. **Services Analytics**
   - **Goal**: Show most requested services.
   - **Files to modify**: `services.html`, `js/services.js` (new).
   - **Implementation**: Increment a `request_count` field in `services.json`; render horizontal bar chart of top services.

### Medium Priority

1. **Barangay Population Comparison**
   - **Goal**: Allow comparison of population across barangays.
   - **Files to modify**: `statistics.html`, `js/main.js`.
   - **Implementation**: Add `renderBarangayComparison()` with selectable barangays; use `population.csv` to generate grouped bar chart.

2. **Legislative Table Interactivity**
   - **Goal**: Sortable, filterable legislative table.
   - **Files to modify**: `legislative.html`, `js/main.js`.
   - **Implementation**: Replace static table with DataTables or custom sort/filter functions.

3. **Weather Enhancement**
   - **Goal**: Add weather widget to index or services page.
   - **Files to modify**: `index.html`, `js/weather.js` (new).
   - **Implementation**: Fetch weather data; display 3-day forecast using cards.

### Low Priority

1. **PhilGEPS Lookups**
   - **Goal**: Searchable procurement records viewer.
   - **Files to modify**: `transparency.html`, `js/philgeps.js`.
   - **Implementation**: Add text filter + paginated results table.

2. **Politicians/Parties Datasets**
   - **Goal**: Display council member affiliation and party breakdown.
   - **Files to modify**: `government.html`, `js/government.js` (new).
   - **Implementation**: Create `politicians.json`; render affiliation badges + pie chart.

## 4. Improvement: Ordinance and Executive Issuance Authorship Display

- **Goal**: Display author(s) of each ordinance/issuance in legislative tables.
- **Schema change**: Add `"authors": ["Rep. Name 1", "Rep. Name 2"]` array to each entry in `legislative.json`.
- **Frontend change**: Update `legislative.html` table columns to include "Author(s)" column; modify `renderLegislativeTable()` in `js/main.js` to display comma-separated authors.
- **Backward compatibility**: If `authors` is missing, display "N/A".

## 5. Authored by Sangguniang Bayan ng Mapandan

All ordinances and resolutions in `legislative.json` are municipal enactments of Mapandan and are authored by the Sangguniang Bayan ng Mapandan.

### Ordinances

- **ORD-1962-001** — Ordinance No. 1, S-1962 — General Municipal Regulatory Code
- **ORD-2020-001** — Ordinance No. 1, S-2020 — Amending Ordinance No. 8, CY 2018 by Authorizing Mayor Anthony C. Peñuliar to Utilize Remaining Funds for Public Market Extension, Motorpool, and Perimeter Wall
- **ORD-2020-002** — Ordinance No. 2, S-2020 — Creating Plantilla Positions Under the Office of the Municipal Treasurer and the Office of the Municipal Planning and Development Coordinator
- **ORD-2021-002** — Ordinance No. 2, S-2021 — Abolishing the Vacant/Unfilled Permanent Position of Agricultural Technologist (SG-10)
- **ORD-2021-003** — Ordinance No. 3, S-2021 — Market Code of the Municipality of Mapandan, Province of Pangasinan
- **ORD-2021-005** — Ordinance No. 5, S-2021 — Creating Sixteen (16) Positions Under the Executive and Legislative Offices
- **ORD-2021-006** — Ordinance No. 6, S-2021 — Authorizing the Proposed Borrowing of the Municipality of Mapandan
- **ORD-2022-001** — Ordinance No. 1, S-2022 — Abolishing Assistant Dept. Head I (SG-22) in Treasury and Creating Executive Plantilla Positions
- **ORD-2023-001** — Ordinance No. 1, S-2023 — Policies and Guidelines for the Operation and Maintenance of Mapandan Public Cemetery and Fee Schedule
- **ORD-2023-002** — Ordinance No. 2, S-2023 — Reclassifying Agricultural Land into Residential Use for Ercy Homes Subdivision
- **ORD-2023-003** — Ordinance No. 3, S-2023 — Reclassifying Agricultural Land into Residential Use (Land Belonging to Named Private Owner)
- **ORD-2023-004** — Ordinance No. 4, S-2023 — Integrated Zoning Regulations of the Municipality of Mapandan for the Term 2022–2032
- **ORD-2023-005** — Ordinance No. 5, S-2023 — Creating Positions Under Executive Offices (Mayor, LDRRM, MSWD)
- **ORD-2024-001** — Ordinance No. 1, S-2024 — Imposing Service Fees for an Offline Method of Encoding Requests for Civil Registry Documents
- **ORD-2024-002** — Ordinance No. 02, S-2024 — Establishing an Animal Bite Treatment Center Under the Municipal Health Office
- **ORD-2024-003** — Ordinance No. 03, S-2024 — Prescribing New Fare Rates for Hire Within the Municipality of Mapandan, Pangasinan
- **ORD-2024-005** — Ordinance No. 5, S-2024 — Reclassification of Parcels of Land from Agricultural to Commercial Use
- **ORD-2024-006** — Ordinance No. 6, S-2024 — Ecological Solid Waste Management, Prescribing Fees, Declaring Prohibited Acts, and Penalties
- **ORD-2024-007** — Ordinance No. 7, S-2024 — Approving and Ratifying Loan Terms with Land Bank of the Philippines for 16 Rescue Vehicles
- **ORD-2025-001** — Ordinance No. 1, S-2025 — Institutionalizing Mental Health Care Program (Adopting R.A. 11036 Provisions & Appropriating Funds)
- **ORD-2025-002** — Ordinance No. 2, S-2025 — Reorganizing Personnel: Abolishing Assistant Registration Officer and Creating Driver I & Registration Officer I
- **ORD-2025-003** — Ordinance No. 03, S-2025 — Granting Benefits and Incentives to Child Development Workers (CDWs)
- **ORD-2025-004** — Ordinance No. 04, S-2025 — Creating the Mapandan Blood Council and 15 Barangay Blood Councils for Voluntary Blood Donation
- **ORD-2025-005** — Ordinance No. 5, S-2025 — Creating Municipal Government Head I (MDRRM Officer) Position Under LDRRMO
- **ORD-2026-001** — Ordinance No. 1, S-2026 — Abolishing Vacant/Unfilled Position of LDRRMO III (Salary Grade 18) Under LDRRMO
- **ORD-2026-003** — Ordinance No. 3, S-2026 — Authorizing ₱45 Million Land Bank Loan for Infrastructure and Development

### Resolutions

- **RES-2018-172** — SB Res. No. 172, S-2018 — Approving Supplemental Annual Investment Program No. 3 CY-2018
- **RES-2021-BAC** — BAC Res. No. 2021-05-011C — BAC Resolution Recommending Single Calculated Responsive Bid — Purchase of Seeds for Farmers
- **RES-2022-075** — SB Res. No. 75, S-2022 — Approving Supplemental Annual Investment Plan No. 1, CY 2022
- **RES-2022-063** — SB Res. No. 63, S-2022 — Approving the Supplemental Annual Investment Plan No. 5, CY 2022
- **RES-2022-070** — SB Res. No. 70, S-2022 — Approving the Supplemental Annual Investment Plan No. 6, CY 2022
- **RES-2023-180** — SB Res. No. 180, S-2023 — Revising the 2023 Annual Investment Plan (AIP) of Mapandan
- **RES-2023-184** — SB Res. No. 184, S-2023 — Approving Supplemental Investment Plan (SIP) No. 3 of the Annual Investment Plan (AIP)
- **RES-2022-066** — SB Res. No. 66, S-2022 — Approving the Annual Investment Plan (AIP) CY 2023 of Mapandan
- **RES-2023-181** — SB Res. No. 181, S-2023 — Adopting the Comprehensive Land Use Plan (CLUP) of the Municipality of Mapandan, Province of Pangasinan
- **RES-2024-287** — SB Res. No. 287, S-2024 — Approving the 2024 AIP Supplemental Investment Plan (SIP) No. 3 of Mapandan
- **RES-2024-344** — SB Res. No. 344, S-2024 — Approving the 2024 AIP Supplemental Investment Plan (SIP) No. 5 of Mapandan
- **RES-2024-299** — SB Res. No. 299, S-2024 — Approving the Annual Investment Plan (AIP) for Fiscal Year 2025
- **RES-2025-050** — SB Res. No. 50, S-2025 — Approving Supplemental Investment Plan No. 2 CY-2025
- **RES-2025-380** — SB Res. No. 380, S-2025 — Approving the 2025 AIP Supplemental Investment Plan (SIP) No. 1 of Mapandan
- **RES-2025-084** — SB Res. No. 84, S-2025 — Approving Supplemental Investment Plan No. 4 of Mapandan
- **RES-2025-067** — SB Res. No. 67, S-2025 — Approving Supplemental Investment Program No. 3 of Mapandan
- **RES-2025-083** — SB Res. No. 83, S-2025 — Approving the Annual Investment Plan CY-2026 of Mapandan
- **RES-2026-125** — SB Res. No. 125, S-2026 — Approving Supplemental Investment Plan No. 1 FY-2026 of Mapandan

## 6. Execution Order

1. Legislative authorship schema + display improvement (foundation for legislative charts).
2. Legislative charts (high priority).
3. Services analytics (high priority).
4. Procurement category breakdown (high priority).
5. Barangay population comparison (medium priority).
6. Legislative table interactivity (medium priority).
7. Weather enhancement (medium priority).
8. PhilGEPS lookups (low priority).
9. Politicians/parties datasets (low priority).

## 7. Validation Criteria

- All charts render without console errors on Chrome/Firefox.
- `legislative.json` passes JSON schema validation after authorship additions.
- Pages load in under 3 seconds on 3G throttling.
- Responsive layout verified at 320px, 768px, and 1440px viewport widths.
- No regression in existing search or table functionality.

## 8. Out of Scope

- User authentication or role-based access.
- Real-time data push / WebSockets.
- Offline-first / PWA features.
- Multi-language / i18n.

## 9. Risks

- PhilGEPS API rate limits or downtime.
- Chart.js version incompatibility with existing dependencies.
- `legislative.json` size may grow; consider pagination/lazy loading.
- Weather API key exposure if client-side only.
