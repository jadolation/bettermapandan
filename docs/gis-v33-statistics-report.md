# V3.3 Restoration and Coverage

The missing implementation was recovered from commit `c54e370c`, present on local
`GIS` and the existing `origin/GIS` remote-tracking branch, but not on `main`.
Remote GitHub API verification timed out; no claim of freshly fetched remote
state is made. Only missing additions were merged into the current architecture.

## Data Inventory

| Input | Actual Fields and Adapter |
| --- | --- |
| `src/data/gis/barangays.geojson` | `gid`, `name`, `slug`, `pop2024`, population year and provenance; exact ten-digit PSGC join |
| `src/data/gis/barangay_boundaries.geojson` | `gid` / `psgc`, polygons; shared indicative display geometry, never assignment evidence |
| `src/data/entities/projects.json` | `project_id`, `canonical_name`, municipality/province, `barangay[]`, source transaction/contract IDs and provenance; existing canonical identities |
| `src/data/dpwh.json` | `projects[]`: transaction/contract IDs, `barangay_location`, `fiscal_year`, `status`; exact identity joins |
| `src/data/fdp_disclosures.json` | `dev_fund[]`: period/year, projects' project/location/pct; inherited normalized-title-plus-barangay canonical key, repeated observations deduplicated |
| `src/data/audit-reports.json` | `infrastructure_projects[]`: ID, explicit location or controlled Barangay/Brgy mentions in name/description, start/completion years; exact provenance, uncertain inherited merges excluded |
| `src/data/procurement.json` | `contracts[]`: title, awardee, award date, amount, status; source-row verification before following explicit project/contract or project/bid/contract relationships |
| `src/data/entities/contracts.json`, `src/data/relationships.json` | Canonical contract IDs/source record IDs; only evidenced `explicit` edges qualify |

## Measured Reconciliation

Current repository inputs produce 15 barangays, 38,228 residents in 2024, and
107 distinct documented canonical projects: 85 assigned and 22 unassigned.

| Source | Examined Records | Included Canonical IDs | Assigned IDs | Unassigned IDs | Unmapped Records |
| --- | ---: | ---: | ---: | ---: | ---: |
| DPWH | 40 | 40 | 36 | 4 | 0 |
| DILG | 146 | 52 | 43 | 9 | 0 |
| COA | 16 | 15 | 6 | 9 | 1 |
| PhilGEPS | 277 | 0 | 0 | 0 | 277 |

PhilGEPS project coverage is unavailable: no qualifying explicit project paths
were established. This is not complete four-source coverage. One inherited
uncertain COA-to-DILG link is excluded. Canonical IDs are enumeration-based, and
DILG identity inherits upstream title/location limitations.

Source, year and status intersect on one reference before canonical-ID union.
Barangay assignment is now retained on that same reference, preventing a location
documented by another source/year from leaking into a filtered count. Per-source
assignment coverage likewise uses that source's own references. Fiscal, disclosure,
start/completion and award years retain their different meanings. Award status is
not construction status. Barangay counts are non-additive for multi-barangay projects.

Zero means no matching documented project in the supported examined scope;
missing/unsupported data remains unavailable. Comparable financial totals and
density remain unavailable. Polygon area differs from historical CLUP territory
figures, so no authoritative density or parcel-level jurisdiction is implied.

## Integration and Evidence

Population and project modes are default-off, using the same boundary renderer
with deterministic tie-preserving green/yellow/red quantiles and gray unavailable
values. Thematic fills are mutually exclusive; markers, outlines and viewport are
preserved. EN/FIL/PAG legends, details, filters and retry behavior are restored.
Map-first accessible heading, default-on boundaries, JavaScript-hidden/no-JavaScript
directories, directory IDs, unresolved facility listings, loaded/details controls,
openpyxl dependency and oversized social-SVG staging exclusion are preserved.

The build emits one bounded `assets/gis/barangay-statistics.json`; exact manifest,
staging and GIS synchronization admit that named JSON only. Regression tests assert
both modes exist and are available in the current real build configuration, even
without a pre-existing artifact.

Validation on restoration:

- Full Python run: 561 passed, 18 skipped, four failures solely from absent raw
  elevation/slope/soil/land-capability PNGs in `tests/test_gis_physical.py`.
- Node runtime: 24 passed; browser fixtures: 30 passed; exact artifact explorer:
  12 passed with controlled Leaflet and external tiles.
- Genuine Leaflet statistics browser: six locale/viewport cases plus two
  missing/malformed resource retry cases; 30 screenshots, zero JavaScript errors.
- Changed Python files pass Ruff. Broad Ruff reports 31 existing issues in
  unrelated build modules; those were not altered.
- Repository CI F-complexity command has no findings. Historical statistics
  builder F/156 was decomposed; its highest function is now D/29.
- Locale key checks pass; existing Pangasinan equal-to-English notices remain.
- Exact artifact audit: 321 HTML pages, 16,257 local href/src references, zero
  missing paths and zero non-exempt SVGs above 100 KiB.

Reproduction uses the locally cached native esbuild binary via
`GIS_ESBUILD_BINARY`, then `python3 build.py --isolated --offline --sync-gis`.
The statistical browser command is
`node tests/browser/gis-statistics.cjs --root "$PWD/_site"`.

Representative screenshots are `/tmp/kilo/gis-v33/gis-en-population-1440.png`,
`/tmp/kilo/gis-v33/gis-en-projects-1440.png`,
`/tmp/kilo/gis-v33/gis-en-projects-390-viewport.png`, and
`/tmp/kilo/gis-v33/gis-en-projects-390-filters.png`.
They use genuine cached Leaflet with neutral offline background tiles, not a live
basemap or a geographic-accuracy certification. Generated site output is not staged
or committed.
