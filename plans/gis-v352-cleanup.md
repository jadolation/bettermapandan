# GIS V3.5.2: Remove Map Positions Text, Counts Text, and Places Layer

## Scope
Three targeted removals in the GIS Explorer:
1. Remove "Map positions (shared coordinates grouped)" text + count
2. Remove "Listed / mapped / list-only / shared coordinates" text + counts
3. Remove the "Places of Interest" layer

## Design Decisions
- The Layers **tab** remains; only the `places` layer entry is removed.
- The `.gis-marker-count` CSS class (clustered-coordinate badge on individual markers) is KEPT — only the `#gis-marker-count` total-count paragraph is removed.
- The `places` layer removal eliminates OSM POI footprints (schools, parks, etc.) from the map. Barangay names/paths/labels and barangay-boundaries are NOT removed.
- The `geometries.places` variable in test fixtures is renamed to `geometries.boundary` since it was only used as polygon geometry for barangay boundary feature testing.

## Changes by File

### 1. Remove "Map positions" text

**`src/pages/gis.html`:**
- Line 8: Remove `data-marker-total="{{GIS_MARKER_TOTAL}}"` attribute
- Line 71: Remove `<p>{{GIS_MARKER_TOTAL}}: <span id="gis-marker-count">0</span></p>`

**`gis/index.html`** (built artifact):
- Line 150: Remove `data-marker-total="..."` attribute
- Line 213: Remove `<p>Map positions...: <span id="gis-marker-count">0</span></p>`

**`assets/gis-map.js`:**
- Line 801: Remove `if (node("marker-count")) node("marker-count").textContent = String(...)`

**`locales/{en,fil,pag}.json`:**
- Remove `"marker_total"` key (line 87 in each file, at `gis` level)

**`tests/test_gis_runtime.py`:**
- Line 168: Add `"GIS_MARKER_TOTAL"` to the removed-tokens assertion list
- Delete line 585: `gis-marker-count` assertion in fallback scenario
- Update line 579: `gis-marker-count` references if any

### 2. Remove "Listed / mapped" counts text

**`assets/gis-map.js`:**
- Lines 269-272: Remove the `if (meta.evacuation_counts) { ... }` block

**`_build/gis_sources.py`:**
- Lines 322-323: Remove `result['metadata']['evacuation_counts'] = {...}`

**`locales/{en,fil,pag}.json`:**
- Remove `"counts"` key inside `gis.resident` (line 38 in each file)

**`tests/test_gis_residents.py`:**
- Line 90: Remove evacuation_counts assertion
- Lines 137-149: Remove places-related assertions (see section 4)

### 3. Remove "Places of Interest" layer

**`src/data/gis/layers.json`:**
- Lines 174-196: Remove the entire `places` layer entry

**`_build/gis_sources.py`:**
- Lines 310-320: Remove the places post-processing block

**`gis/index.html`:**
- Remove `places` layer from `window.GIS_LAYERS` JSON

**`tests/test_gis_data.py`:**
- Line 44: Remove `places` source assertion
- Lines 58-59: Remove `places.geojson` assertions
- Line 70: Update geojson output count (was 5: facilities, barangay-halls, barangay-boundaries, dpwh-projects, places → now 4)

**`tests/test_gis_residents.py`:**
- Lines 137-149: Remove places canonical_facility_id assertions

**`tests/browser/gis-explorer.cjs`:**
- Line 43: Remove `layer("places", ...)` from fixture layers
- Line 351: Rename `places` geometry to `boundary`
- Lines 367-368: Replace `geometries.places` with `geometries.boundary`
- Line 371: Remove `places` from URL regex
- Line 503: Remove `"places"` from layer toggle list
- Update any test assertions that depend on places layer loading

**`tests/browser/gis-markers.cjs`:**
- Line 56: Remove `'places'` from layer toggle list
- Line 60: Remove `['places','']` from search iteration

### 4. Test adjustments for fixture geometry rename

**`tests/browser/gis-explorer.cjs`:**
- The `geometries.places` Polygon was used for barangay boundary features in tests. Rename to `geometries.boundary` and update all references (lines 351, 367-368).

## Files NOT Changed
- `assets/css/map.css` — `.gis-marker-count` badge CSS retained
- `src/data/gis/barangay_halls.geojson` — unchanged (15 halls preserved)
- `src/data/gis/facilities.geojson` — unchanged (legacy halls already suppressed)
- `src/data/gis/barangay_boundaries.geojson` — unchanged
- `src/data/gis/barangays.geojson` — unchanged (barangay labels preserved)
- `tests/gis-runtime.cjs` — no places references found
- `_build/gis_halls.py` — unchanged
- `_build/gis_residents.py` — the places post-processing is in `gis_sources.py`, not here

## Validation
- Python: `pytest tests/test_gis_halls.py tests/test_gis_data.py tests/test_gis_residents.py tests/test_gis_runtime.py -q`
- Node: `node --test tests/gis-runtime.cjs`
- Browser fixtures: run gis-explorer.cjs and gis-markers.cjs
- Build: `python3 build.py --isolated --offline --sync-gis`
- Check: no `places` references remain in `gis/index.html` GIS_LAYERS
- Check: no `evacuation_counts` or `marker_total` in output JSON
