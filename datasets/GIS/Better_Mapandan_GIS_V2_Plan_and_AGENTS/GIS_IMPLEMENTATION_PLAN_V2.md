# Better Mapandan GIS — Remediation & Expansion Implementation Plan (v2)

**Date:** 19 October 2026  
**Repository:** `jadolation/bettermapandan` — `GIS` branch, reviewed at `15a584a4`  
**Purpose:** Replace the sparse GIS prototype with an evidence-first, accessible municipal geographic explorer; integrate six municipal/PHIVOLCS map sources without overstating accuracy.  
**Status:** Implementation proposal; no changes to GitHub have been made.  
**Companion:** `AGENTS.md` and `data/` staging directory.

## 1. Executive decision

Retain Python static generation, Leaflet, GeoJSON, vanilla JS and GitHub Pages. Introduce a **typed manifest-driven layer registry**, a **spatial ETL and release gate**, and a **GIS explorer UI**. Treat the six supplied maps as **historical/source evidence**, not inherently coordinate-accurate GIS polygons. Favor original PHIVOLCS KMZ GroundOverlays over poster-image traces. Candidate GIS geometries in this package must not be published as authoritative or used for exposure/safety computations.

### Outcomes

- A resident can search barangays and public facilities, inspect sourced details, enable available mapped layers and understand precision/date limitations.
- Maps are available only when an actual browser asset and compatible renderer exist; unavailable layers show actionable explanations.
- No claim that a point is a surveyed position, an evacuation facility is officially designated, or a municipal/barangay boundary is legally authoritative without appropriate evidence.
- GIS links reliably to the canonical Better Mapandan infrastructure/project explorer without inventing coordinates.

## 2. Existing architecture: findings and fixes

| Finding (GIS branch) | Correction | Acceptance |
|---|---|---|
| `assets/gis-map.js` registers only `Municipal Extent` and `Public Facilities`; manifest lists roads, places, projects, hazards | Manifest-driven layer loader, GeoJSON point/line/polygon and raster image overlay adapters; validate URL, type, publish state, attributions | Every selectable layer has an accessible tested resource and working renderer |
| Blue dashed map rectangle represents extraction bounds, not a municipality polygon | Rename `Data coverage extent`, off by default, or remove when reviewed municipal geometry exists | No `Municipal Boundary` label on approximate bbox |
| Barangays have `geometry: null` | Preserve PSGC metadata; separately stage traced polygon candidates for review | No fabricated polygon; 15 barangay records remain linked by PSGC |
| Facility 16-point map uses approximate Plus Code cell centers | Show location-precision labels, location vs source verification, source detail | Popups say `approximate location` unless verified otherwise |
| `src/pages/gis.html` lists static facility notice, no filtering or map↔list sync | Search/filter, interactive feature panel, select/list ↔ map event links | Keyboard and mobile UI tested |
| `layers.json` references data under `datasets/GIS` and KMZ but build doesn't export browser-ready layers | Spatial ETL exports only approved `dist/assets/gis/` files | No dead URLs or false toggle affordances |
| `_build/pages.py` injects raw JSON into executable `<script>` blocks | External JSON `fetch`, or HTML-safe embedding (escape `<`, `>`, `&` and U+2028/U+2029) | Malicious sample `</script>` cannot escape data context |
| Facility publication filter excludes `blocked_feature_ids` but doesn't independently prove all gate conditions; malformed object returns raw | Fail closed, typed validation for status, geometry, provenance, open review conflicts, artifact allowlist | Rejected features never appear in HTML/JSON or index |
| Hazard disclaimer and legend are always visible despite no hazards rendered | Conditional layer info/legend, source dates and clear non-operational disclaimer | Active overlay determines legend/disclaimer |
| Locale titles in manifest but hardcoded English map UI | Locale bundle EN/FIL/PAG with fallbacks visibly reported | UI strings and map descriptions tested in 3 languages |
| Generated root deployed wholesale | Dedicated public output directory | Only approved public files shipped |
| Tests exist but branch delivery gates need verified execution | GIS unit, integration and browser tests; require passing checks before deployment | CI blocks failed integrity/security/browser checks |

## 3. Six-map source inventory and extractable classes

**Map A — Ground shaking**: PHIVOLCS, map dated **February 2022**, approximate scale **1:10,000**. Legend: **PEIS intensity VIII or higher** (very destructive–devastating), **VII** (destructive), **VI** (very strong). Supplied image `phivolcs_ground_shaking_2022.png` (original `image(6).png`). Existing GIS branch source: `datasets/GIS/gsh_2022_015528000_01.kmz`. The screenshot visibly shows widespread VIII-or-higher color, but **no percentage or per-barangay footprint should be asserted without georeferenced raster/vector classification**. Display as georeferenced raster after validation; retain 2022 scenario/limitations in legend.

**Map B — Liquefaction**: PHIVOLCS, map dated **December 2025** per original map caption, approximate scale **1:10,000**. Legend: **High** red, **Moderate** purple, **Low** yellow. Supplied image `phivolcs_liquefaction_2025.png` (`image(7).png`); existing source `datasets/GIS/liq_2024_015528000_01.kmz`. **The filename suggests 2024 while the image caption says December 2025: investigate version and provenance before treating them as the same dataset.** Some map areas are uncolored/background; do not assign those a hazard class without legend verification. Do not equate susceptibility with an event forecast.

**Map C — General elevation**: Municipality of Mapandan/MPDC, **15 December 2012**, scale **1:30,000**, legend **1, 4, 8, 12, 16, 20, 24, 28 m above sea level**. Image `municipal_elevation_2012.png` (`image(8).png`). Historical terrain classification, **not a continuous elevation DEM**. Text says municipality extremes 1 m (Angalacan River between Coral and Baloling) and 28 m (reported at Primicias/Luyan). Extracted 15 barangay range attributes are in `data/mapandan_barangay_elevation_reference.csv`.

**Map D — General slope**: Municipality/MPDC, **15 December 2012**, scale **1:30,000**; **0–3%** (blue) and **3–8%** (orange/coral); historical source text reports ~86.57% and ~13.43% by area. Image `municipal_slope_2012.png` (`image(9).png`). Experimental color segmentation in `data/general_slope_UNVALIDATED_color_polygons.geojson` is NOT spatially validated. Do not compute area from that file.

**Map E — General soil classification**: Municipality/MPDC with BSWM as classification source, **15 December 2012**, scale **1:30,000**. Legend: San Manuel Fine Sandy Loam (green), San Manuel Silt Loam (yellow), San Manuel Silty Clay Loam (pink/red), River Wash (gray). Image `municipal_soil_2012.png` (`image(10).png`). Reported table: Silt Loam 674.495 ha / 31.62%; Silty Clay Loam 16.707 ha / 0.78%; Fine Sandy Loam 1905.779 ha / 65.92%; River Wash 35 ha / 1.68%. **Areas sum 2631.981 ha, not stated 2132.704 ha**; do not normalize silently.

**Map F — General land capability**: Municipality/MPDC, **15 December 2012**, scale **1:30,000**. Legend shows **Class A** (blue; good cultivable land) and **Class B** (orange; needs conservation practices). Accompanying text describes **Class X** (wet/swamp) as well but image does not map an X class. Image `municipal_land_capability_2012.png` (`image(20261019-074417).png`). Reported A = 1765.08 ha / 82.77%; B = 331.340 ha / 15.54%; X = 35.723 ha / 1.68%; class area sum = **2132.143 ha**, not MPDC municipal **3291.752 ha**. Experimental `data/land_capability_UNVALIDATED_color_polygons.geojson` includes only image-interpreted colors, not X geometry.

### Source crosswalk and geometry status

| Asset | Extracted data | Geographic status | Public policy |
|---|---|---|---|
| `data/mapandan_gis_extracted_reference.json` | all six class legends, dates, municipal facts, slope/soils/land capability | Attributes, **not georeferenced** | May publish *labeled facts* after editorial checks; do not portray as GIS geometry |
| `data/mapandan_barangay_elevation_reference.csv` | 15 elevation ranges, names | Attributes only, no outlines | Join to canonical PSGC after QA |
| `data/municipality_outline_CANDIDATE.geojson` | 104-vertex approximate traced outer outline | **Experimental affine grid mapping**, not surveyed | Internal QA only; no public `Municipal Boundary` |
| `data/barangay_LABEL_ANCHORS_UNVALIDATED.geojson` | 15 approximate text-label anchor points | Cartographic label positions, not centroids | Internal QA only |
| `data/general_slope_UNVALIDATED_color_polygons.geojson` | tentative color regions for 0–3 / 3–8% | Unverified segmentation, distorted by text/linework | Internal QA only |
| `data/land_capability_UNVALIDATED_color_polygons.geojson` | tentative colors A/B | Unverified segmentation, excludes textual X | Internal QA only |
| PHIVOLCS KMZ in repository | raster GroundOverlay source candidates | Inspect KML LatLonBox/rotation and ground truth | Publish raster only after matching versions, georegistration, usage rights |

**Important:** The six image files were supplied by the user from the municipal website and PHIVOLCS. Attribution alone does not establish republication permission; confirm terms/licenses/permissions for public hosting of derivatives.

## 4. Extracted nonspatial Mapandan reference facts

- Province Pangasinan; Region I; **15 barangays**; MPDC/CLUP total area **3,291.7520 hectares**; assessor reported **2,459.6652 taxable-scope hectares**, excluding roads, water and other non-taxable lands; urban core **288.291 hectares**; rural **3003.461 hectares**.
- RHU c.y. 2023 population **43,722**, households **10,685**. Separately, GIS branch PSA 2024 population **38,228**. Keep different methods/vintages; never silently overwrite.
- Physical-characteristics prose mentions dry October–April, wet May–September, August wettest, temperatures **25.55–34.28 °C**. Historical climatic descriptions, not live climate normals or forecasts.
- Sources report major watercourses Angalacan River, Payas Creek, Tulong/Matulong Creek, Colos Creek, irrigation canals. **No reliable line geometries have been extracted from prose.** Historical drainage distances/areas have unit ambiguities; retain verbatim with flags.
- Historical development includes original pueblo establishment **28 December 1887**, reorganization **1908**, and move of center from Torres to present Poblacion. Suitable for map contextual history, not geometry.
- Map graticules in MPDC images approximately **120°25′12″–120°28′48″ E**, **16°00′00″–16°02′24″ N**. User-supplied prose separately reports `120°56′`, an apparent mismatch. Do not use prose longitude as control point.

### Barangay elevation attributes (reported, in meters)

| Barangay | Min | Max | Type per supplied text |
|---|---:|---:|---|
| Poblacion | 8 | 16 | Urban |
| Coral | 12 | 16 | Rural |
| Apaya | 12 | 16 | Rural |
| Aserda | 8 | 16 | Rural |
| Nilombot | 8 | 12 | Rural |
| Pias | 8 | 16 | Rural |
| Baloling | 8 | 16 | Rural |
| Primicias | 16 | 24 | Rural |
| Torres | 12 | 16 | Rural |
| Luyan | 12 | 16 | Rural |
| Jimenez | 12 | 16 | Rural |
| Golden | 8 | 12 | Rural |
| Santa Maria | 12 | 16 | Rural |
| Amanoaoac | 12 | 16 | Rural |
| Lambayan | 12 | 16 | Rural |

**Reconcile conflicting urban classifications:** supplied older text says one urban barangay (Poblacion), while canonical GIS-branch barangay data may classify other barangays differently. Both must retain source/as-of fields; no destructive merges.

## 5. Data engineering and spatial ETL

Suggested working paths consistent with existing repo:

```text
datasets/GIS/raw/                      # original images/KMZ and retrieval proof (if reuse permitted)
datasets/GIS/derived_unvalidated/      # do NOT deploy: copied staging candidates
src/data/gis/                         # reviewed entities, accepted GIS metadata, schemas
src/data/gis/review/                  # review decisions and uncertainty records
_build/gis/                            # new ETL: raster, vector, provenance, validation
assets/gis/                            # only approved/generated browser assets
assets/js/gis/                         # map, layers, search, details, i18n, interaction
tests/test_gis_*.py                    # data + build integration
tests/browser/gis.spec.*               # Playwright browser/keyboard/mobile
```

**Implement pipelines:**

1. Source registry: `id, agency, original_url, original_filename, published_at, retrieved_at, license_basis, original_crs, map_scale, original_hash, source_version`.
2. Georeference: prefer PHIVOLCS KMZ/KML metadata; for 2012 MPDC poster maps calibrate from grid crossings and independent reliable geographic control points, explicitly recording residual error and uncertainty.
3. Raster products: crop to map panel without removing map source/legend from traceable archive; produce web-optimized transparent raster/tiles with bounds; validate overlay alignment visually on OSM at multiple zooms.
4. Vector products: trace municipal boundary first for QA; topology-clean 15 barangays only after source geometry is sufficiently supported; `geometry: null` remains canonical otherwise.
5. Classification: annotate legend categories, palette, scenario/date, nodata, sampling limitations; **never derive quantitative class areas from screenshot pixel counts**.
6. Normalize CRS: web GeoJSON WGS84 longitude/latitude; carry native CRS/transform/precision metadata; maintain source master geometry unchanged.
7. Public filter: validate feature ID, source, geometry, review state, precision and open blockers; allowlist published attributes; only approved files enter dist.
8. Test and release: run reconciliation checks, geometry validity, layer URL checks, HTML-safe JSON tests, visual map review, and provenance/license checks.

**Trace/QGIS acceptance criteria:** source registration documented; minimum 4 well-spread independent control points for simple transform (more for complex deformation), recorded residuals in both pixels/meters where possible, no unjustified fixed universal accuracy threshold; reviewer signs off on intended viewing scale. Match canonical PSA/PSGC IDs and require non-overlap/topology checks before publishing reference barangay polygons.

## 6. Public GIS UX specification

Desktop: header → full-height searchable map workspace, **left layer/search/filter sidebar**, central Leaflet map, **right feature details drawer**. Mobile: map + accessible bottom-sheet drawer. Keep map zoom/location stable when toggling layers. Use category icons distinct from verification status. Include `Fit Mapandan`, reset, scale bar, source and uncertainty controls; optional locate-user only with explicit browser permission.

- Sections: **Administrative**, **Public Facilities**, **Roads & Places**, **Infrastructure Projects**, **Physical Geography (2012)**, **Hazards (2022/2025)**.
- Manifest states: `available`, `reference_only`, `pending_georeference`, `pending_permission`, `blocked`, `deprecated`. Disable unavailable layer toggles with explanation, and never claim these are implemented.
- Layer types: `geojson-point`, `geojson-line`, `geojson-polygon`, `raster-image-overlay`, `wms` (approved only). Each exposes `legend`, `source`, `source_date`, `accuracy`, `limits`, `attribution`, `bounds` and `default_visible`.
- Select a barangay from search: show 2024 PSA stats and historical elevation range; fly to **reviewed polygon** only when available, otherwise display barangay reference without fictitious center.
- Facility popups: verified source versus location verification, `approximate` coordinate notice, original record link and address; do not use `source_verified` as an unconditional spatial accuracy claim.
- Project popups: only projects with defensible point geometry get markers; barangay-only projects are listed under associated barangay without exact pins.
- Hazard legend appears only for active, validated overlays; do not offer safety, evacuation, or travel-routing guarantees.
- Map controls and strings translate EN, FIL, PAG; persistent accessibility labels, focus control, non-color legends, keyboard support.

## 7. Deliverable phases and release criteria

**P0 — Safeguards (must precede feature expansion):** fail-closed publication filter; safe embedded data or external files; release manifest schema; strip review internals; prevent project/feature coordinates fabricated from names. **Done when:** malformed blocked sample fails build, no rejected feature in output.

**P1 — GIS explorer v0.2:** responsive layer/search/sidebar/details architecture; facilities (existing 16, explicitly approximate), OSM roads/places where reviewed, accurate categories, available-layer registry. **Done when:** layer toggle, filtering, focus, popups work on phone and desktop, and data paths resolve.

**P2 — Six-map references:** publish factual 2012/2022/2025 layer descriptions, classification legends and attribute data; show **disabled** imagery until rights/georeferencing approved. **Done when:** users see dates/limitations and no misleading overlays.

**P3 — Georeferenced layers:** inspect PHIVOLCS KMZ KML metadata, resolve 2024-vs-2025 filename mismatch, convert verified ground-shaking and liquefaction overlays; QGIS-register 2012 elevation/slope/soil/land capability imagery; optional municipality outline as clearly reviewed historic/cartographic boundary. **Done when:** visual alignment QA, permission check and reviewer signature attached.

**P4 — Barangay topology:** obtain better administrative source when possible; trace and validate 15 polygons with PSGC correspondence, QA adjacency/edge gaps and assign `cartographic_reference` precision. **Done when:** polygon count IDs and topology pass; old `null` remains if data fails.

**P5 — Transparency integration:** map defensibly geolocated DPWH projects and public facilities to Better Mapandan Project Explorer, with evidence levels. **Done when:** every map claim traces to a canonical project ID and geographic provenance.

**P6 — Analysis and future feeds:** only with suitable licensed authoritative hazard geometry and precision can you calculate overlay intersections. Introduce near-real-time weather/advisory feeds only as separately labeled streams. **Done when:** model/data limitations clearly documented and safety review complete.

## 8. Mandatory QA checklist

- [ ] Verify SHA-256, source date, map scale, original URL, reuse permission for all six originals.
- [ ] Check whether PHIVOLCS `liq_2024...kmz` represents map captioned 2025 (do not assume equivalence).
- [ ] No publishable geometry from candidate traced polygons until georeferencing and human QA.
- [ ] Confirm map graticule and record residuals; compare boundaries to independent source.
- [ ] Preserve conflicting MPDC area tables exactly with warning and provenance.
- [ ] Maintain RHU 2023 vs PSA 2024 population separately.
- [ ] Show layer legend classes and historical date; add non-real-time hazard warnings.
- [ ] Manifest entries correspond to real browser assets and working renderer.
- [ ] Reject `</script>` injection and malformed GeoJSON/coordinates in build.
- [ ] Verify review blockers/status before public export and exclude internal reviewer notes.
- [ ] Run pytest, GIS-specific integration, accessibility and mobile browser tests in CI.
- [ ] Scope deployment to a public distribution directory, without raw/review data.

## 9. Known data-quality issues

See `data/mapandan_gis_quality_flags.csv`. Key anomalies: soil class areas **2631.981** vs reported **2132.704 ha**; land capability class areas **2132.143** vs reported municipality **3291.752 ha**; slope table misaligned 86.57% in an area column; RHU/PSA population differences; prose longitude `120°56′` conflicting with graticules; river length unit ambiguity; historical single-urban-barangay description may differ from later statistics.

**Never silently correct data.** Show source-reported numbers and an audit note. Do not issue calculated flood coverage, evacuation suitability, or hazard impact statistics based on poster-derived candidate shapes.

## 10. Artifact/package manifest

- `data/mapandan_gis_extracted_reference.json` — canonical research-stage factual extraction (contains all six layer legends and 15 barangay ranges).
- `data/mapandan_barangay_elevation_reference.csv` — attributes to join to canonical PSGC records.
- `data/mapandan_gis_quality_flags.csv` — source discrepancies.
- `data/municipality_outline_CANDIDATE.geojson` — historical outline candidate, unvalidated.
- `data/barangay_LABEL_ANCHORS_UNVALIDATED.geojson` — 15 text positions, not centroids.
- `data/general_slope_UNVALIDATED_color_polygons.geojson` — experimental segmentation, unvalidated.
- `data/land_capability_UNVALIDATED_color_polygons.geojson` — experimental segmentation, unvalidated.
- `previews/boundary_trace_preview.png` — candidate trace visual audit.

**Scope note:** This package does **not** contain 15 verified barangay polygons, georeferenced PHIVOLCS raster layers, exact roads extracted from poster pixels, or validated per-barangay seismic/liquefaction classifications. These are future tasks, not accomplished outputs.
