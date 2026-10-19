# AGENTS.md — Better Mapandan GIS v2 Development Rules

> **Applies to:** the `GIS` branch of `jadolation/bettermapandan`, especially `src/data/gis/`, `datasets/GIS/`, `_build/`, `assets/gis*`, `assets/js/gis/`, `src/pages/gis.html` and tests. **Read** `GIS_IMPLEMENTATION_PLAN_V2.md` and the repository's original `datasets/GIS/AGENTS.md` before editing. This file supplements—not silently overrides—the original evidence/safety rules. If requirements conflict, stop and seek human review; prefer the rule that prevents misleading publication.
>
> **State:** This is a prepared file to be placed in the repository; it has **not** been committed. Experimental images and GeoJSON are **not authoritative geometry**.

## Mission

Build a trustworthy, usable Mapandan GIS explorer on the existing static Python + Leaflet + vanilla JS + GeoJSON stack. Connect mapped facilities/infrastructure to canonical municipal records only where sources substantiate the relation. Improve user experience without fabricating precision, boundaries, hazards, evacuation suitability or real-time accuracy.

## Hard rules (non-negotiable)

1. **No invented geometry.** Never create municipal/barangay polygons from barangay names, hall points, plus codes, nearest-neighbor guesses, generative AI output, or uncalibrated image tracing. Never label the bounding rectangle `Municipal Boundary`.
2. **Never elevate candidate geometry.** The imported `municipality_outline_CANDIDATE.geojson`, `barangay_LABEL_ANCHORS_UNVALIDATED.geojson`, `general_slope_UNVALIDATED_color_polygons.geojson` and `land_capability_UNVALIDATED_color_polygons.geojson` are research artifacts only. Not public map overlays, administrative facts, hazard-exposure inputs, or numeric area sources without completed QGIS georeferencing, review and documented approval.
3. **Source status is not positional accuracy.** `source_verified` alone does not mean exact location, identity, designation, open/operational status, or field verification. Approximate Plus Code cell centers must be labeled approximate.
4. **Safety:** GIS hazards are historical/model-based, not live earthquake prediction, flood forecasting, shelter availability, evacuation guidance or safe routing. No safety conclusions from intersecting approximate location points with coarse raster images. Show map date, scenario, source, legend, limitations.
5. **Review and reproduce:** Every publishable geographic fact has `source_id`, source URL/document, retrieved date, published/as-of date, geometry method, accuracy limitations, reviewer/status and license/rights review. Store original source unchanged, derivative separately, transformation method and hashes.
6. **Never silently fix conflicts:** Preserve original reported values and include `quality_flags`. E.g., soil area entries total 2,631.981 ha vs stated 2,132.704 ha; land capability entries total 2,132.143 ha vs MPDC area 3,291.752 ha; RHU 2023 population 43,722 vs PSA 2024 population 38,228; prose longitude `120°56′` vs map-grid ~`120°25′–120°29′`.
7. **Human verification for disputed facility coordinates.** Review queue conflicts must be resolved with named/documented evidence; never auto-open the publication gate merely because a maintainer marked a source record verified.
8. **No assumption that source availability grants rights.** Map images are from municipal and PHIVOLCS sources, but separate public redistribution/derivative licensing review is required. Do not publish original full-size map image or a derivative raster without documented permission or established applicable reuse terms.
9. **Fail closed.** Missing manifest, corrupt GeoJSON, missing provenance, unauthorized license status, unsupported renderer, invalid CRS/geometry, unresolved review blocker, or unsafe HTML serialization must fail build or leave a clearly unavailable layer—never expose raw data by fallback.
10. **No unapproved GitHub modification.** Implement in working files/branch only as instructed; do not force-push or modify `main` without explicit approval.

## Existing GIS branch context

- `assets/gis-map.js` currently registers only approximate extent + facilities, even though `src/data/gis/layers.json` defines more layers.
- `src/data/gis/barangays.geojson` contains 15 PSGC records with `geometry: null`. Preserve that pending validated geometry.
- `src/data/gis/facilities.geojson` has 16 source-verified candidates; approximate Plus Code geometry and review issues warrant distinct location labels.
- `datasets/GIS/highways.geojson` and `places.geojson` are candidate OSM exports; publish via a dedicated approved ETL, not just manifest references.
- Source KMZ files `gsh_2022_015528000_01.kmz` and `liq_2024_015528000_01.kmz` require internal KML georeferencing and metadata inspection. Poster liquefaction image says **2025**, while KMZ filename says **2024**—verify before merging.
- `_build/pages.py` GIS facility publication filter is partial and must be replaced by schema/provenance/status/issue-aware allowlist; it currently risks returning malformed input unchanged.
- JSON appended to inline `<script>` must be replaced with fetched JSON or serialized safely for HTML script context.
- The user-provided six-image extraction pack is staging material, not approved geography.

## Extracted six-map reference facts to preserve

| Map | Year/date on source | Legend / content | Output status |
|---|---|---|---|
| PHIVOLCS Ground Shaking | February 2022 | PEIS VIII or above: very destructive–devastating; VII: destructive; VI: very strong | Prefer native KMZ; hazard poster reference only until verified |
| PHIVOLCS Liquefaction | December 2025 on poster | High (red), Moderate (purple), Low (yellow) | Resolve 2024 KMZ versus 2025 poster version; no automated zones |
| MPDC General Elevation | December 15, 2012 | 1, 4, 8, 12, 16, 20, 24, 28 m classes | Reference raster and 15 barangay range attributes; not DEM |
| MPDC General Slope | December 15, 2012 | 0–3% and 3–8%; reported shares 86.57%, 13.43% | Experimental segmentation blocked |
| MPDC Soil Classification | December 15, 2012 | San Manuel Fine Sandy Loam, San Manuel Silt Loam, San Manuel Silty Clay Loam, River Wash | Reference data only; inconsistent area table |
| MPDC Land Capability | December 15, 2012 | Image: Classes A and B; accompanying text: Class X wetlands | Do not invent X spatial polygons; area table inconsistent |

Historical reference: MPDC municipal area 3,291.7520 ha; assessors' different-scope area 2,459.6652 ha; historical urban 288.291 ha, rural 3,003.461 ha; 15 barangays; elevation 1–28 m; slope 0–8%; RHU 2023 population 43,722, households 10,685. Source classes and full attribute rows are in `data/mapandan_gis_extracted_reference.json` and `data/mapandan_barangay_elevation_reference.csv` within the handoff package, to be relocated into appropriately named versioned research/derived paths if reviewed.

### Barangay reported elevation ranges, meters

- Poblacion 8–16; Coral 12–16; Apaya 12–16; Aserda 8–16; Nilombot 8–12;
- Pias 8–16; Baloling 8–16; Primicias 16–24; Torres 12–16; Luyan 12–16;
- Jimenez 12–16; Golden 8–12; Santa Maria 12–16; Amanoaoac 12–16; Lambayan 12–16.

Do not generalize these reported barangay ranges to specific parcels/points or derive contours from them. Older text states only Poblacion is urban; do not overwrite different PSA-era classifications.

## Agent execution protocol

**Before writing code:**

1. Check branch/commit and `git status`; inspect original repository `datasets/GIS/AGENTS.md` and plan; search for equivalent existing components.
2. List every manifest entry with referenced path/type and whether actual browser assets and loader exist.
3. Inventory `src/data/gis/`, review queue, source KMZ, existing OSM dataset shape, page build hooks and tests.
4. Identify missing or contradictory data. Do not invent missing structures or report unavailable data as usable.
5. Write a small concrete change plan naming touched files, tests, and public data impact.

**Development phases:**

- **P0 safeguards:** fail-closed publication filtering; external JSON or properly escaped HTML-safe serialization; explicit dataset schema; no unintended raw research files in deployed output; layer manifest publication states.
- **P1 frontend:** searchable/filterable layer sidebar, selected-feature details, keyboard/mobile design, connected facility list, reviewed roads/places, map controls and provenance; preserve existing architecture.
- **P2 source facts:** integrate six map legend metadata with dates and limitations; add municipality facts, barangay elevation attributes keyed by canonical PSGC after review. Ungeoreferenced images remain off-map.
- **P3 raster processing:** inspect native PHIVOLCS KML GroundOverlay and native KMZ, verify version/permission, produce georeferenced raster assets; QGIS register historical MPDC sheets to audited control points and record errors; no rough visual hacks.
- **P4 administrative geometry:** obtain or digitize candidate polygons from sufficiently registered original maps with reviewer signoff, PSGC, valid topology and confidence; never claim legal boundary.
- **P5 entity integration:** map only geolocated, evidenced DPWH projects; barangay-only projects in textual filtered list, not fabricated points.
- **P6 spatial analysis/live:** only after accuracy/data-rights review; live feeds separated from reference/historical maps and never used for emergency operational claims.

After each phase, document what actually works, pending datasets, test results, generated files, and blockers. No blanket "complete" if layers are still unavailable.

## Layer schema and supported renderers

Example fields (implementation suggestion, not current repo schema):

```json
{
  "id": "historic-slope-2012",
  "title_key": "gis.layer.historic_slope",
  "category": "physical_geography",
  "type": "raster-image-overlay",
  "status": "pending_georeference",
  "public_url": null,
  "source_id": "mapandan-mpdc-general-slope-2012",
  "source_date": "2012-12-15",
  "source_crs": "pending_validation",
  "bounds": null,
  "accuracy_note": "Historical map; not georeferenced",
  "legend": ["0–3%", "3–8%"],
  "default_visible": false
}
```

Explicit adapters: GeoJSON point, line, polygon; registered raster image overlays; and authorized WMS. Each selectable layer MUST have a published data URL and matching renderer. Validate bounds are geographically meaningful (not invented). Attribution and dates are required. Do not silently hide load errors.

## Build-time release gate

For each feature: verify schema, known geometry type, valid finite coordinates ordered `[longitude, latitude]`, coordinate range, canonical ID, source provenance, record currency, review state, publication eligibility, and the public-only property allowlist. Record open issues independently of `source_verified`. Reject malformed datasets; never `return raw_json` after validation failure. Remove review notes, internal personal details and candidate source conflicts from output unless deliberately summarized for public use.

For each raster: verified bounds, CRS, registration/transform evidence, map date/scenario/legend, source rights, reviewer signoff. For each polygon: geometry validity, orientation, no self-intersection, expected footprint bounds, topology checks where partition claims exist. No numeric area claims from experimental segmentation.

Use `dist/` or an equivalent clean artifact directory rather than uploading repository root. Make release reproducible: pin dependencies and tool versions, run tests and block publication on failure. Do not modify source datasets in place during site build.

## Tests to add or update

- GeoJSON syntax, `FeatureCollection`, IDs, bounds, source metadata, geometry presence/absence, CRS expectations.
- Strict approval of public facility status; source/location status separate; unresolved blocker wins.
- `municipality_outline_CANDIDATE` and `*_UNVALIDATED*` cannot appear in `dist/` / deployed `layers.json` as selectable layers.
- Original 15 PSGC codes and population logic unchanged; maintain conflicting historical demographic vintages separately.
- Barangay elevation join to exactly 15 records without assuming coordinates or overwriting newer canonical classification.
- Numeric anomaly checks comparing reported/observed sums and recording expected warning IDs.
- Manifest validity and resource existence; overlays fail gracefully if remote WMS unavailable.
- Safe HTML injection regression: string `</script><script>alert(1)</script>` does not execute when inserted into data.
- Browser keyboard navigation, screen-reader labels, responsive phone view, map/list selection synchronization and translated strings.
- PHIVOLCS KMZ provenance/version mismatch triggers review rather than silent linking.
- Run `python -m pytest tests/ -q` in quality CI; run Playwright on GIS page. Ensure production deploy depends on successful jobs.

## UX principles

- Explain categories with ordinary language; keep advanced GIS terms in a metadata drawer.
- Display **map source**, **as-of date**, **location precision**, **verification distinction**, **legend**, and **limitations** for selected items.
- No `Verified facility` chip for approximate coordinates without supporting precision label.
- A candidate layer remains visibly `Not available — awaiting verification` rather than showing an inert checkbox.
- Do not overwhelm map with huge persistent hazard warnings when no hazard overlay is active. Show a concise site-wide reference disclaimer and layer-specific caution when opened.
- Preserve the English, Filipino and Pangasinan build; translated feature labels and error states.
- Use semantic controls, focus management, accessible list + map equivalents; color must not be the sole hazard cue.

## Requirements for any coding-agent completion report

Report: files changed; actual working functionality; input sources and versions; which layers are public, internal, pending or blocked; georeferencing residuals/review approvals if produced; validation/test commands and results; unresolved precision/permission issues; screenshots or previews if feasible. **Never state hazard overlays, polygon boundaries, or disaster analysis are complete unless the required verification gates passed.**
