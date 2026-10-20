# Better Mapandan GIS — Implementation Plan V3
**Version:** 3.0 · 20 October 2026  
**Goal:** Integrate the existing DPWH project locations, render 15 clickable barangay boundaries, and display four historical physical-characteristics maps in the existing Leaflet GIS Explorer. No data-approval workflow, backend database, or separate publication mode.

## Decision and data availability
**Use an existing polygon dataset first. Do not crop 15 barangay images as separate map layers.** A public nationwide source exists: `bendlikeabamboo/barangay-boundaries-repository`, GitHub release `v2026.4.13.0`, file `barangays.geojson` (data derived from NAMRIA administrative geometry and PSA PSGC; release curates a 2023-10-24 PSGC snapshot and NAMRIA 2023-11-06 geometry; geometry simplified with Douglas–Peucker tolerance 0.005 degrees). Its Mapandan subset has **not been downloaded or validated in this planning session** because the release download was inaccessible to this environment. Therefore, no 15-polygon GeoJSON is claimed to have been delivered. Run the included extractor against the downloaded release before adopting it.

Primary release: https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases/tag/v2026.4.13.0  
Direct download: https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases/download/v2026.4.13.0/barangays.geojson  
Upstream repository: https://github.com/bendlikeabamboo/barangay-boundaries-repository

**Fallback:** Use GeoRiskPH/PSA boundary service where access and export permissions allow, or request polygon shapefiles from Mapandan MPDC or NAMRIA. If neither supplies all 15 acceptable polygons, digitize the missing/incorrect sections from a georeferenced municipal map. Clearly describe any derived boundaries as *approximate reference boundaries, not legal/surveyed boundaries*.

## New reference images — what they support
1. **Mapandan Barangay (Water district).png:** delineates and labels all 15 barangays on top of imagery and water-pressure symbology. Useful as the principal visual guide for relative shape and topology. Its legend represents water pressure, *not* elevation, terrain, or barangay classification. Map coordinates/control-point metadata are not embedded in the rendered image; its pixels are not immediately GeoJSON geometry.
2. **MAPANDAN_BARANGAYS.png:** shows a second, simplified colored subdivision view, but includes numbered units **1–4** and a truncated label for Santa Maria. Treat it as a **secondary comparison**; do not convert numbered regions into official barangay names without supporting source metadata. Its outlines appear schematized, so it is not automatically more geodetically accurate than a properly sourced GeoJSON.
3. Older **municipal elevation/slope/soil/land-capability maps (circa 2012):** include graticule ticks and named internal administrative lines, which help georeferencing and cross-validation, but reflect an earlier map vintage. Confirm coordinate reference interpretation before fitting.

Expected barangays (15): Amanoaoac, Apaya, Aserda, Baloling, Coral, Golden, Jimenez, Lambayan, Luyan, Nilombot, Pias, Poblacion, Primicias, Santa Maria (also Sta. Maria), Torres.

## Phase 0 - integrate existing DPWH projects

**Goal:** Reuse the data already powering the infrastructure map rather than creating another map or entering project coordinates again. This phase can deliver value independently of polygon acquisition and historical scan preparation.

**Source:** `src/data/dpwh.json`. At the time of inspection it contains **40 projects: 38 with numeric latitude/longitude and 2 without coordinate pairs**. These are observed counts, not permanent acceptance constants; the adapter must validate actual coordinate values and tolerate normal dataset edits.

1. Add a DPWH-specific adapter in the existing GIS preparation modules. Convert finite, in-range `longitude` and `latitude` values into GeoJSON Points in **[longitude, latitude]** order. Preserve records with missing or invalid coordinate pairs as searchable nonspatial entries with an explanatory note; do not invent positions or silently swap/repair coordinates.
2. Preserve the source transaction identifier, project name, category, fiscal year, contractor, contract amount, status, accomplishment percentage, relevant dates, and source information. Extend the existing safe property projection to retain the required numeric and text fields. Reject duplicate source identifiers with an actionable diagnostic rather than merging unrelated records.
3. Establish canonical project links using explicit source identifiers. `_build/entities.py` must preserve the DPWH transaction identifier and any actual contract identifier during entity generation; do not assume an absent `contract_id` supplies the transaction identifier. Resolve an exact relationship to the canonical project ID, never by project-name similarity, record order, or nearby coordinates. If no unambiguous relationship exists, retain the record and link to the existing infrastructure page/record where supported.
4. Replace the current `dpwh-projects` configuration, which reads `src/data/entities/projects.json` as nonspatial references, with the DPWH source adapter. Keep broader canonical references separately named **Project References**. Deduplicate search results by an explicit canonical relationship where the same project appears in both representations; do not suppress unmatched records or nearby projects.
5. Render the layer under **Facilities & Infrastructure** using the existing lazy-loading and vector pipeline. Supply localized status-colored points and a legend for Completed, Ongoing, Not Yet Started, and an unknown/other fallback. Keep coordinate-sharing records individually inspectable without jitter. Integrate search, layer filtering, selection, details, fit/reset, keyboard controls, and mobile layout; no additional authorization flags are required.
6. Keep the existing infrastructure map functional and reading the same `src/data/dpwh.json` source. Do not embed its complete map into the Explorer or maintain a second manually edited copy of the project data. Its specialized filters may remain separate from the Explorer's controls.
7. Emit the derived spatial/nonspatial layer through the existing generated GIS resource inventory. Verify inclusion in `_site/` and optional `--sync-gis` root synchronization, including correct EN/FIL/PAG project links. No acknowledgment files, approval records, or separate build modes.

**Acceptance:** Every source record remains inspectable; every structurally valid coordinate-bearing project can be selected on the map; missing-position records remain searchable without fabricated geometry. Tests cover coordinate order/ranges, missing optional fields, duplicate identifiers, shared coordinates, status legend, details, exact canonical links and fallback, all three locales, and coexistence with facilities, barangays, and hazard overlays. Marker-group counts may be lower than positioned-record counts where coordinates coincide. The original infrastructure map must continue working.

## Phase 1 — acquire and verify geometry (mandatory for barangay polygons)
1. Download the published `barangays.geojson` release locally. Keep it out of the served `_site/` and repository if too large.
2. Use `extract_mapandan.py` (included here): it detects candidate PSGC fields, filters by **Mapandan municipality prefix `0105528`** and/or location fields, prints diagnostic candidates, and exports ONLY if the expected 15 names/codes are matched. **Inspect the output and extracted source properties before using it.** PSGC representations vary by snapshot; do not silently guess prefixes.
3. Verify 15 distinct polygons, name and 10-digit PSGC correspondence against existing `src/data/gis/barangays.geojson`, and Polygon/MultiPolygon geometry validity. Reject missing, duplicate, or misassigned units.
4. Compare with the water-district map: relative neighborhood topology; Baloling/Pias along north; Nilombot/Golden west; Luyan/Torres and Primicias southeast; watercourses and major roads. Inspect overlaps and gaps in QGIS. A visual match is not proof of survey accuracy.
5. Record the source, date/vintage, license attribution, simplification, and geographic limitations in a short sidecar `barangay_boundaries_sources.json`. No approvals, signatures, or hash ledgers.
6. If mismatches materially affect barangay selection, try a more detailed authoritative shapefile or correct boundaries in QGIS against properly georeferenced local sources. Preserve original untouched; label a corrected derivative and document edits. If 15 cannot be confirmed, do not fabricate them: publish verified subset and show missing ones in directory.

**Output:** `src/data/gis/barangay_boundaries.geojson` (new); `src/data/gis/barangay_boundaries_sources.json` (new).

## Phase 2 — connect spatial geometry to canonical barangay references
- Keep `src/data/gis/barangays.geojson` as the canonical directory with existing PSGC, name, and population; `geometry: null` is fine here.
- Add a **distinct polygon layer** rather than forcing directory records through the existing `reference` adapter. Join polygon records to directory records by a normalized PSGC code, never by geometric proximity. Validate all 15 relationships and surface unmatched entries.
- Add a `barangay-boundaries` `geojson` layer entry in `src/data/gis/layers.json`: enabled, visible by default, with source label/date, location precision, and limitations.
- Ensure `_build/gis_preview.py` preserves allowed `gid`, `psgc`, `name`, and provenance fields; `_build/gis_sources.py` generates `assets/gis/barangay-boundaries.geojson`; `_build/staging.py` and root sync inventory include the file.
- In `assets/gis-map.js`, draw outlines with low-opacity fill; click / keyboard selection highlights the polygon, fits it, and displays the directory record. Searching the barangay name should find it without enabling an unrelated layer. When polygon data is unavailable, retain the static directory and clearly label the absent map geometry.
- Source-safe value display: name, PSGC, 2024 population and date, rural/urban category only if substantiated, reported barangay elevation range, polygon-source vintage/precision, and optional links. Never present a historical figure as current without its year.

**Acceptance:** all 15 expected barangays appear as selectable shapes, if and only if their actual geometries were obtained and verified; no disabled “Barangay Reference” checkbox misleadingly presented as a drawable layer.

## Phase 3 — four physical-characteristics overlays
1. Elevation; 2. Slope; 3. Soil Classification; 4. Land Capability.
- Keep original municipal scans as source/reference documents in a sensible source directory, separate from public processed tiles.
- In QGIS, crop to **only geographic map content**; exclude legend frame/title and outer borders. Georeference using multiple graticule intersections and map-to-ground control features, validate at independent points, and export transparent warped GeoTIFF or appropriately aligned PNG plus geographic bounds (EPSG:4326). Prefer GeoTIFF for preparation; build transforms into web-displayable assets.
- Caution: `L.imageOverlay()` with a simple west/south/east/north box is **not** a replacement for rubber-sheet warping on a distorted scan. QGIS must warp/rectify first; rotated/sheared scans need proper transformation. Do not assign full poster bounds to the map viewport.
- Extend `_build/gis_sources.py` to support a **local, known-bounds raster** layer format (or package each rectified image as a supported GroundOverlay KMZ) without general-purpose raster engine in JS. Validate bounds, file size, and image dimensions. Output runtime `raster-image-overlay`, a source date, attribution and legend.
- Group controls under **Physical Characteristics** with mutually convenient selection (single prominent thematic map at a time), per-map opacity slider, legible legend, and a short 2012/historical-vintage notice. Barangay outlines and facilities remain visually above thematic rasters; set Leaflet panes/z-index and pointer interaction accordingly.
- Do NOT infer a precise elevation value / soil type from a clicked pixel unless actual classified GIS data is independently available. Allow raster **source description only**, while barangay popup shows pre-recorded summary data where supported.
- Soil/land capability tabular area totals in the supplied historical text are internally inconsistent: preserve *reported* values with their source and include a note; do not reconcile silently.

## Phase 4 — refine UX (without changing architecture)
- Organize sidebar as Administrative, Physical Characteristics, Natural Hazards, Facilities & Infrastructure. Place the spatial DPWH layer in Facilities & Infrastructure; present nonspatial project references distinctly instead of implying they are drawable overlays.
- Maintain `Explore` vs `Map layers` tabs, search and keyboard navigation, mobile bottom-sheet details, localized EN/FIL/PAG titles, legends, reset/fit, and no-JS directories.
- Hazard imagery remains separate from physical maps; avoid two high-opacity rasters obscuring the map at once. User-chosen opacity persists while toggling layers within the current session.
- Keep simple attribution for NAMRIA/PSA, municipal MPDC, PHIVOLCS/GSI, and OSM according to each data source.

## Phase 5 — tests and completion
**Data:** DPWH source-record coverage, finite in-range point positions, retained nonspatial records, unique identifiers, and exact canonical links where available; exactly 15 named/PSGC-matched polygons when source supports this; finite coordinates, valid rings, no unexpected intersections/duplicates, sensible municipality extent; visually compare neighborhood adjacency against both uploaded images; test high and low zoom alignment against roads/watercourses. Watch for significant errors due to source generalization (0.005 degrees is coarse at barangay scale). Derive DPWH counts from input fixtures rather than freezing the current 40/38/2 inventory.

**Build:** `python build.py --isolated --offline`, verify generated `_site/assets/gis/` manifest and three locales; `--sync-gis` only if running the intentional root-mirror workflow.

**Browser:** automated Leaflet test with positioned and nonspatial DPWH projects, status-colored points, shared-coordinate selection, correct project links, all 15 barangay clicks when geometry exists, correct directory join, layer toggles, opacity, legend, search, keyboard, raster loading, fit bounds, mobile, missing data fallback, and independent hazard/facility rendering. Verify the existing infrastructure map remains functional. Serve `_site` over HTTP to check tiles and generated assets in EN/FIL/PAG; verify synchronized root routes separately when `--sync-gis` is used.

**Deliverables:** DPWH adapter and generated project layer, explicit source-to-canonical identifier links where available, localized status legend and project details, preserved original infrastructure map; generated `barangay-boundaries.geojson` *after successful source validation*; four georeferenced overlay outputs and legend definitions; updated GIS config/build/runtime/style; tested pages; concise provenance notes. Maintain a single build and simple source-file editing—**no approval gates or extra review ledger**.

## Contingencies and non-goals
- **If the public NAMRIA-derived polygon release does not include a matching Mapandan feature set:** investigate the source codes and alternate service, then digitize as fallback. Do not invent the missing polygon coordinates.
- **If the municipal scans cannot be georeferenced sufficiently:** expose them in a standalone source-map viewer until control points are established; do not misplace them on the Leaflet basemap.
- No legal boundary certification, parcel-level decisions, flood forecasting, pixel-specific hazard classification, or emergency navigation.

## Implementation order
1. Integrate the existing DPWH project dataset, positions, details, and explicit links while preserving its infrastructure map.
2. Retrieve 15 barangay polygons and verify code correspondence and topology.
3. Make the clickable barangay layer with joined canonical references.
4. Georeference and display the four physical-characteristics maps as source inputs become available.
5. Complete sidebar organization, opacity controls, legends, and interaction ordering.
6. Run full build/browser/localization checks and deploy through the existing tested-artifact workflow when release is requested.

This order delivers value early without risky all-at-once refactoring. DPWH integration does not depend on obtaining new barangay polygons or missing historical scans; completion of those later deliverables still depends on actual usable source material.
