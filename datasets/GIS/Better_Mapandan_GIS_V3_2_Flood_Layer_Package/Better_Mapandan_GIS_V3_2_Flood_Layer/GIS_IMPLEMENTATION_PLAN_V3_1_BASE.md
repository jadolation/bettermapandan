# Better Mapandan GIS — Implementation Plan V3.1

**Date:** 20 October 2026  
**Purpose:** Complete clickable Mapandan barangays and add four historical physical-characteristics layers **within the existing working static Python + Leaflet GIS Explorer**.  
**Status:** Implementation plan; no repository edits, georeferencing, or new runtime tests performed in this package.

## 0. Executive decision and scope

- **Do not rebuild the GIS interface.** Retain the existing `Explore` / `Map layers` tabs, Leaflet map, search, results and details panel, EN/FIL/PAG localization, no-JS directories, hazard KMZ support, facilities, DPWH integration, source metadata, and `_site` workflow.
- **Use the extracted ADM4 candidate GeoJSON** delivered with this package instead of the highly generalized triangular polygon source, subject to the geographic checks in Phase 1. The new file already has all 15 expected barangay names and 10-digit `gid` identifiers, with geodetic polygon coordinates. It is a **candidate, not certified jurisdictional geometry**.
- **Add four historical physical layers:** Elevation, Slope, Soil Classification, Land Capability. Their original poster images are included under `sources/physical/`; they are **not yet georeferenced** and must not be displayed by blindly stretching the entire posters to Mapandan's bounding box.
- **Maintain one public build**, source-controlled JSON/GeoJSON/rasters, no approval ledgers, hashes, separate research mode or backend database. Keep ordinary validation/escaping/static-path hygiene.

## 1. Inputs bundled and provenance

| Input | Bundled path | Current state | Intended use |
|---|---|---|---|
| 15-barangay ADM4 candidate | `sources/barangay/mapandan_barangay_boundaries_ADM4_candidate.geojson` | Existing extracted GeoJSON, 15 named features, EPSG:4326 lon/lat | Replace coarse reference geometry after checks |
| Candidate shape preview | `sources/barangay/mapandan_barangay_ADM4_candidate_preview.png` | Preview, not georeferencing evidence | Side-by-side QA |
| Water-district barangay map | `sources/barangay/Mapandan Barangay (Water district).png` | Labeled thematic reference with internal divisions | Relative layout and adjacency comparison |
| Colored barangay schematic | `sources/barangay/MAPANDAN_BARANGAYS.png` | Schematic with some numeric/unresolved subdivision labels | Secondary comparison only |
| Original elevation poster | `sources/physical/elevation.png` | Historical municipal poster, not georeferenced | Historical elevation raster overlay |
| Original slope poster | `sources/physical/slope.png` | Historical municipal poster, not georeferenced | Slope raster overlay |
| Original soil poster | `sources/physical/soil_classification.png` | Historical municipal poster, not georeferenced | Soil classification raster overlay |
| Original land capability poster | `sources/physical/land_capability.png` | Historical municipal poster, not georeferenced | Land capability raster overlay |

**Source specifics:** The physical posters are municipal MPDC map products dated **12 December 2012** on their artwork (confirm any finer source data vintage from the print). The second ADM4 shapefile upload lacks its DBF, but the **first** `BgySubMuns.shp.*` set was usable for candidate extraction. Keep the shapefile source citation supplied with the candidate; do not claim its derivative has been surveyed. The extracted file should be compared against the upstream source/version before permanent publication.

**Known area discrepancy:** The earlier extraction reported candidate polygon union **about 20.44 km²**, while the supplied historical CLUP describes **3291.7520 ha = 32.91752 km²**. The difference is substantial. Different historical/administrative measurement definitions may be involved, but this is **not resolved**. Do not present geometry-derived barangay area or total territory as official. Confirm municipal extent, geographic alignment, source year, expected administrative coverage, and whether polygons cover all land before claiming full boundary quality. Valid rings and no overlaps do not solve an extent mismatch.

## 2. Phase 1 — Replace coarse barangay source with useful candidate polygons

**Goal:** 15 selectable polygon shapes with correct canonical identities. Existing directory records remain authoritative for the site's population and PSGC information.

1. Preserve the original `src/data/gis/barangays.geojson` (15 null-geometry reference records) and the currently deployed very-coarse source for rollback/inspection; **do not conflate reference data and geometric features**.
2. Load the bundled `mapandan_barangay_boundaries_ADM4_candidate.geojson` in QGIS and inspect feature names, `gid` strings, Polygon/MultiPolygon validity, CRS EPSG:4326, bounding box and topology. Expect exactly one feature per barangay: Amanoaoac, Apaya, Aserda, Baloling, Coral, Golden, Jimenez, Lambayan, Luyan, Nilombot, Pias, Poblacion, Primicias, Santa Maria, Torres.
3. Join against existing `barangays.geojson` using **exact 10-digit PSGC `gid`**. Preserve leading zero; normalize only verified `Sta. Maria`/`Santa Maria` variants for display, not identity. Fail visibly on duplicate or unmatched `gid`. Existing population fields retain their source year, not inferred from shape.
4. **Geographic review:** overlay candidate boundaries on OSM and candidate preview; compare locations, adjacency and internal divisions against the water-district map and colored schematic. Investigate Luyan, Amanoaoac, Aserda (relatively straight edges) and northern/southeastern outline. Check contiguous coverage, overlaps, slivers, municipalities touched, and why total candidate area differs from CLUP. Verify against a better municipality boundary if available. Retain candid limitations if source differences remain.
5. Save a compact provenance note beside the geometry: dataset attribution/URL, date/vintage if known, CRS, geometry description, area comparison, uncertainty, visual checks and any manual changes. **Not a review/approval ledger**.
6. Replace or supersede the old `very coarse barangay source geometry` entry: use display title **Barangay Boundaries (Indicative)** and a non-alarming but honest note: "Source-derived indicative boundaries; not for legal or parcel-level jurisdiction decisions." Keep it toggleable and visually inspectable while geographic mismatch remains. Do **not** automatically claim official area or exact address jurisdiction.
7. Keep a distinctly named polygon `geojson` layer (`barangay-boundaries`) rather than converting the nonspatial `Barangay Reference` directory into drawable geometry. Reuse the existing GIS GeoJSON pipeline; do not invent a new data format.

**Acceptance:** 15 distinct valid polygons, 15 precise PSGC joins, no material accidental overlap, clicks and search show correct barangay; area discrepancy documented; neither the UI nor generated metadata calls boundaries "surveyed". Compare geographic quality before enabling by default. If mismatch remains major, off by default but readily available is safer than promoting inaccurate boundaries.

## 3. Phase 2 — Interactions for every barangay

**Existing implementation:** The app already renders polygons and maintains selected feature/details state. Extend the existing renderer, not a separate map widget.

- Click/tap polygon → selected outline/fill highlight, details with barangay name, PSGC, 2024 population with citation/vintage, and **municipal reference elevation range** if joined from historical data (year shown). Zoom/fit only at the user's request or on search selection, so clicking does not unexpectedly reset view.
- Clicking a label/list entry selects the matching polygon where geometry is present. Selecting a barangay whose shape is unavailable still displays directory data without relocating the map.
- Keep selected barangay geometry **above physical/hazard rasters** using Leaflet panes; raster overlays should not consume clicks. Keyboard selection/search and accessible close/focus behavior should continue working.
- Use subtle borders and `fillOpacity` approximately 0.05–0.15; distinguish hover/selected styling. Label polygons with safe HTML/DOM text; avoid clutter at municipality-wide zoom.
- Do not derive point-in-polygon jurisdiction or geographic area statistics from candidate geometry until the quality review resolves the extent mismatch.

## 4. Phase 3 — Four historical physical-characteristics maps

### Maps and original legend meanings

| Layer | Original municipal categories / interpretation | UI behavior |
|---|---|---|
| Elevation (2012) | Legend indicates classes at 1, 4, 8, 12, 16, 20, 24, 28 m above sea level; map uses colors and contour lines | Raster toggle, original legend, opacity control; describe values as historical classes |
| Slope (2012) | 0–3% and 3–8% categories with mapped zones (blue vs reddish/orange) | Raster toggle, category legend, opacity |
| Soil Classification (2012) | San Manuel Fine Sandy Loam; San Manuel Silt Loam; San Manuel Silty Clay Loam; River Wash | Raster toggle, text/color legend, opacity |
| Land Capability (2012) | Map visibly codes Class A and Class B; accompanying historical text discusses Class X but geographic X extent is not visibly separable on this poster | Raster toggle, legend faithfully matching map, opacity, textual Class X caveat |

**Do not silently repair source inconsistencies:** Historical soil table reported class areas do not reconcile cleanly with printed total. Land capability area totals also do not reconcile cleanly with the larger CLUP municipality area. Keep these as *reported historical figures* in supporting text, with year and source, not computed GIS measurements. Do not claim precise soil/elevation/hazard class for a clicked address based merely on poster pixel color.

### Raster preparation workflow — required once per map

1. **Preserve originals** under `datasets/GIS/physical/originals/` or equivalent maintainer source directory; four images in this package are the input posters, not production geographic overlays.
2. Identify the cartographic map frame for each. **Exclude legends, title, north arrow, margins, and surrounds from the geographic overlay.** Crop/rectify the map portion separately while preserving source images.
3. Georeference in QGIS Georeferencer using graticule crossings on the source posters and independent ground control from suitable coordinates/features. Confirm the printed coordinate reference/grid and axis order first. Use several well-spread control points and withhold some as independent checks. Report transformation type and residual errors in *meters* at Mapandan's location; avoid making up an accuracy threshold.
4. Warp/rectify each raster into a coordinate-aware intermediate (GeoTIFF in suitable CRS), then export to **EPSG:4326-aligned**/Web-Mercator-compatible visual output with transparent outside pixels. Do not just wrap a rotated/skewed poster into southwest/northeast Leaflet bounds. If using simple `L.imageOverlay`, the resulting rectified PNG must align with a single north-up bounding rectangle; otherwise prefer an actual georeferenced tiled raster workflow.
5. **Inspect outside Mapandan and map edges**: clip the thematic raster to an appropriate municipal mask only after checking the mask's credibility. Never use the suspect 20.44 km² candidate polygons as a truth mask merely to make edges look clean. Keep transparency outside map footprint.
6. Build the existing runtime `raster-image-overlay` type either by emitting rectified PNG + checked bounding coordinates or by preparing a supported KML GroundOverlay KMZ; reuse `_build/gis_sources.py`'s raster packaging rather than writing a GIS back end. Ensure `assets/gis/manifest.json` lists four outputs, URLs resolve in `_site` and root mirror where applicable, and all three locale pages link to the same assets.
7. Add four independent `layers.json` entries with IDs `physical-elevation`, `physical-slope`, `physical-soil`, `physical-land-capability`, `enabled=true`, `visible_by_default=false`, type matching the preparer, `semantic_role`, pane `physical`, original source/MPDC attribution, print date, precision/limitations, and **hand-transcribed faithful legends**.
8. In UI group them under **Physical Characteristics**. Favor a one-at-a-time thematic-raster option in this group so legends remain readable; user can still toggle outlines, facilities and roads over it. Keep hazard toggles separate. Each displayed raster has opacity 0–100%, sensible starting opacity (~55–65%), and a historical reference disclaimer. Switching off/on should preserve opacity and current map viewport.
9. Validate at multiple zooms and against fixed points: graticule lines, major intersections, river crossings, relative placement of the southern/SE hills, and the municipal outline. If registration is not adequate, **present the original poster in a reference-map viewer** rather than placing it inaccurately on Leaflet.

### Rendering hierarchy

Basemap tiles → physical rasters → hazard rasters → barangay polygons/labels → roads/projects → facilities and selected features. Existing app already uses ordered panes and pointer-event protections; extend them. Legends must be per-layer and derived from actual source legend, not inferred from color-segmentation outputs.

## 5. Phase 4 — UX and information model

- Sidebar group order: **Administrative** (indicative barangay boundaries, directory), **Physical Characteristics** (4 new maps), **Natural Hazards** (ground shaking, liquefaction), **Infrastructure** (roads, places, DPWH projects), **Facilities**.
- The nonspatial `Barangay Reference` must be visually a **directory link/tab**, not a disabled checkbox implying map drawing. Polygon layer gets its own functional checkbox.
- Keep search/filter and source/details controls; a single prominent thematic raster legend, per-map opacity, three locale labels EN/FIL/PAG, map loading/error messages and mobile usability.
- Preserve hotlines/non-real-time hazard disclaimer and existing site content. Ticker horizontal overflow can be fixed separately; do not scope-creep GIS implementation into unrelated site redesign.
- Optional future improvement: proper classified GIS polygons for soil/slope only if source geodata becomes available; **not required for V3.1**.

## 6. Phase 5 — integration, tests and deployment

**Files likely to change (inspect real current implementation before editing):** `src/data/gis/layers.json`, `src/data/gis/barangay_boundaries.geojson`, source provenance JSON, `_build/gis_sources.py`, `_build/gis_preview.py`, `_build/gis_boundaries.py` (only where needed), `assets/gis-map.js`, `assets/css/map.css`, `src/pages/gis.html`, locale JSON, unit/browser GIS tests, `_build/staging.py`/`_build/gis_sync.py` as needed for generated resource inventory.

**Build commands:** `python build.py --isolated --offline`; if intentionally serving the root mirror, `python build.py --isolated --offline --sync-gis`; otherwise serve `python -m http.server 8000 --directory _site` and browse `/gis/`, `/fil/gis/`, `/pag/gis/`.

**Tests:**
- 15 geometry features; correct names/`gid`; no duplicate join IDs; polygon validity/CRS; source metadata retained; extent/coverage-area discrepancy explicitly audited.
- Selecting any barangay on map/list opens its canonical details; highlight/keyboard/mobile; layer switch does not reset viewport; no duplicate search entries.
- All four physical maps load one by one in Chrome, with correctly colored/aligned overlays, correct legend text, attribution, source year, opacity control, and click-through to polygons/points. Check at multiple zooms and on mobile.
- Missing/bad raster leaves other layers functional; broken GIS input reports clear issue rather than blank site.
- Three locale routes and static directory contents; `_site/assets/gis/manifest.json` contains every output; no stale root/`_site` asset mismatch; no unintended files staged.
- Existing roads, facilities, DPWH and two hazard layers still function.

**Deliverables:**
1. `src/data/gis/barangay_boundaries.geojson` (from bundled candidate only after validity/visual review) and short source/quality metadata.
2. Four source-backed georeferenced raster outputs plus `layers.json` definitions, original legends and dates.
3. Clickable barangay polygons joined to directory data and localized UX.
4. Geographic alignment and area-discrepancy report with illustrative comparisons, *not* approval records.
5. Passing browser/build tests and functioning static build.

## 7. Coding-agent instructions / non-goals

- **Work in the current GIS branch/working tree**; check files before changing. Avoid old plans that required manual publication approvals. Do not claim tests passed without running them.
- Use only actual coordinates from source. No random smoothing, guessed polygon buffers, snapping polygons to fill an area for appearances, invented classifications, or blind poster-to-bbox overlays.
- It is acceptable to **publish indicative mapped features** with an honest caption and proper source attribution; don't block basic presentation on irrelevant governance paperwork.
- Do not build a database, server, ML map color classifier, routing engine, exposure calculator, emergency decision model, or other unrelated systems.
- If the imagery is georeference-limited, ship a polished standalone original-map viewer with source and legend instead of misleading coordinates; say exactly what's blocked.

## 8. Suggested sequence for agent execution

1. Compare current GIS source and bundled candidate; implement the 15 PSGC-linked click polygons with quality notice; test.
2. Import and prepare **one** physical source map (slope is a straightforward first trial), prove georeferencing and render/legend/opacity end-to-end.
3. Repeat the same proven procedure for elevation, soil, and land capability.
4. Finalize sidebar, localization, mobile polish and tests; export the same `_site` artifact served locally and deployed.

**Completion means a working GIS with 15 inspectable barangays and four correctly registered historical thematic layers—not merely four PNGs saved in the repo.**
