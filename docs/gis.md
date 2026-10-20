# GIS Maintainer Workflow

Edit repository data, choose layers, rebuild, and view the map. The maintainer's
selection is sufficient for inclusion; no acknowledgment, approval ledger, pinned
source hash, or GIS-specific environment configuration is required.

## Build and View

Install the project dependencies once, then build from the repository root:

```sh
python3 -m pip install -r requirements.txt
python3 build.py --isolated --offline
python3 -m http.server 8000 --bind 127.0.0.1 --directory _site
```

Open <http://127.0.0.1:8000/gis/>. Filipino and Pangasinan are at `/fil/gis/` and
`/pag/gis/`. The isolated build uses a disposable workspace and exports `_site/`;
it does not replace the checkout's legacy generated page trees.

VS Code Live Server is configured with root `/_site` and port `5501`. After
building, start Live Server and open <http://127.0.0.1:5501/gis/index.html>
(or `/fil/gis/` and `/pag/gis/`). Restart an already-running Live Server after
changing its root. `liveServer.settings.file` is a **404 fallback**, not a start
page setting, so it is deliberately not configured.

### Optional Root GIS Mirror

The main editable layout is `src/pages/gis.html`, with shared styles/scripts in
`assets/` and text in `locales/`. `_site/` is the preferred preview server root.
For tools that must open the canonical checkout routes, explicitly rebuild and
refresh just the generated GIS root mirror:

```sh
python3 build.py --isolated --offline --sync-gis
```

`--sync-gis` requires `--isolated`. It runs **after** the fresh staged build and
copies `gis/index.html`, `fil/gis/index.html`, `pag/gis/index.html`, required
generated CSS/JS, referenced unchanged images/fonts, and the exact generated
`assets/gis/manifest.json` resources (including locale copies). It does not copy
other linked pages, wipe locale directories, replace raw scripts/styles, or
touch source datasets. Existing referenced raw assets must match the stage;
otherwise synchronization refuses to overwrite them. Only stale GIS derivatives
listed in the previous generated manifests are removed; unrelated files remain.
All inputs and destinations are checked before root changes. A refused sync
leaves the existing root mirror intact, though the fresh `_site/` is still usable.
Ordinary isolated builds remain isolated and never update this mirror.

Integration tools can call `synchronize_gis(root, site=None)` from
`_build.gis_sync` after a fresh build; `site` defaults to `root / "_site"` and
the return value is the sorted list of copied repository-relative `Path` objects.
There is one map workflow, without modes, approval steps, or permission ledgers.

`--offline` avoids downloading build tooling. It does not make the browser's CDN
libraries or map tiles available offline. Pillow, included in the Python
requirements, validates images extracted from supported KMZ inputs.

## Edit a Facility

Edit a feature in `src/data/gis/facilities.geojson`. Keep a stable unique ID,
`geometry.type: "Point"`, and coordinates in **longitude, latitude** order. Supply
finite, in-range coordinates from your source; do not guess a location from a
name. Update display properties such as `name`, `category`, `source`,
`source_url`, `source_as_of`, and `location_precision` when known. Preserve the
file's existing feature/property structure and precision vocabulary.

Every structurally valid supplied facility point is included. A missing review
record or verification date does not hide it. Source/precision information is
descriptive, not a claim of independent verification. Private review notes and
coordinate-history collections are not needed in normal browser payloads.

## Choose Layers

`src/data/gis/layers.json` is the layer list. Each entry has a unique `id`, a
localized `title`, input `type`, repository-relative `source`, boolean `enabled`,
and boolean `visible_by_default`. Set `enabled` to `false` to omit a layer and its
resources. `visible_by_default: false` keeps an enabled layer available in the
explorer without initially displaying it.

Supported input types are `geojson`, `records`, `dpwh`, and `kmz`. Paths must stay within
`src/data/` or `datasets/GIS/`; external URLs, traversal, and unsafe symlinks are
not inputs. `source_url` is optional provenance, not a URL to fetch during a
build. Use optional `source_label`, `attribution`, `source_date`, `precision`,
and `limitations` for honest source/precision text.

Optional localized `group: {"en": "...", "fil": "...", "pag": "..."}` labels organize
the layer picker. `pane` is one of `physical`, `hazards`, `administrative`,
`infrastructure`, or `facilities`; `opacity` is a finite number from 0 to 1.
`exclusive_group` is an optional nonempty string for physical overlay selection,
not an approval mechanism. `dependencies` lists up to ten small repository-local
build inputs, such as the descriptive boundary sidecar. Isolation copies these
before the child build, not the entire original boundary archive.

To add a vector layer, save a GeoJSON FeatureCollection such as
`src/data/gis/landmarks.geojson`, then add an entry to the existing `layers`
array. This is a complete minimal configuration example, not a request to
replace the existing configured layers:

```json
{
  "layers": [
    {
      "id": "landmarks",
      "title": {
        "en": "Landmarks",
        "fil": "Mga Palatandaan",
        "pag": "Landmarks"
      },
      "type": "geojson",
      "source": "src/data/gis/landmarks.geojson",
      "enabled": true,
      "visible_by_default": false
    }
  ]
}
```

The configuration includes facilities, roads, places, barangay reference records,
source-reported DPWH project points, all canonical Project References, optional
very coarse barangay source geometry, and supported ground-shaking/liquefaction
KMZ overlays. Records without supplied valid geometry remain searchable
nonspatial records; project links use exact canonical IDs when matched. No points are invented.
Approximate extraction bounds are not administrative boundaries. Experimental
traced outlines, label anchors, and color-segmented polygons are not selected;
their research originals and historical V2 handoff files remain unchanged.

## DPWH Projects

The `dpwh` loader reads `src/data/dpwh.json` and emits
`assets/gis/dpwh-projects.geojson`. `_build.gis_projects.dpwh_collection` is a pure
adapter over the source and generated canonical project list. Every one of the
40 source records is retained as a supplied Point or null geometry, with source
transaction ID, source status plus controlled status key, contractor, category,
fiscal year, contract/budget/accomplishment values, actual source dates, precision,
and limitations. It does not turn a project point into a footprint or alignment.

Canonical links require a unique exact `source_transaction_id` match, not name
similarity or a guessed ID. Otherwise the link targets that source record in the
infrastructure directory. The separate `project-references` layer retains all
107 canonical nonspatial records. `GIS_RECORDS` carries each record's `layer_id`
so the runtime can scope references and avoid default-list duplicates for exact
canonical matches. DPWH records also appear in the escaped static/no-JS directory.
No canonical coordinates, reference populations or project IDs are changed here.

## Coarse Barangay Geometry

`src/data/gis/barangay_boundaries.geojson` preserves the coordinates of exactly
15 source polygons from the local repository's
`2023-10-24/hierarchical_t0p005/barangays.geojson`. The join requires exact
`ADM3_PCODE=PH0105528` and `ADM4_PCODE=PH` plus each canonical ten-digit `gid`,
cross-checking `psgc_code` when present. Names and populations come from the
unchanged canonical directory; original names remain `source_name`. The original
detailed shapefiles are absent. Repository lineage describes NAMRIA geometry
enriched with PSA PSGC, not independent verification of this local derivative.

Actual analysis with temporary Shapely 2.2.0 and pyproj 3.8.0, measured in
WGS84 / UTM zone 51N (EPSG:32651), found six triangles and nine quadrilaterals.
All are individually valid, but they do not form a usable administrative partition:

| Measurement | Square Kilometres |
| --- | ---: |
| Sum of individual simplified geometry areas | 15.88685 |
| Union | 15.45135 |
| Same-source simplified municipality | 18.81759 |
| Overlap excess | 0.43550 |
| Municipality not covered | 4.76356 (25.31%) |
| Outside municipality | 1.39732 |
| Source municipality `AREA_SQKM` metadata | 20.41576 |

The comparison municipality is itself simplified, not a detailed authoritative
control. `AREA_SQKM` is retained pre-simplification metadata, not measured shape
area. The descriptive sidecar `barangay_boundaries_sources.json` records source
and comparison hashes, library versions, per-feature measurements and warnings;
it is not an approval file. No gaps or overlaps have been repaired or concealed.

Because these defects are material, the selectable layer is explicitly titled
**Very coarse barangay source geometry**, uses role `barangay_reference_geometry`,
and is **off by default**, not advertised as `barangay_boundary`. The null-geometry
canonical directory stays primary when this layer is off. Do not use these shapes
for parcel, routing, service-area or hazard analysis. A reliable detailed boundary
layer remains missing; images have not been used to invent extra detail.

Extraction is an explicit development operation, not a build-time archive scan:

```sh
python3 -m _build.gis_boundaries \
  --input datasets/GIS/barangay-boundaries-repository-main/barangay-boundaries-repository-main/2023-10-24/hierarchical_t0p005/barangays.geojson \
  --canonical src/data/gis/barangays.geojson \
  --municipality datasets/GIS/barangay-boundaries-repository-main/barangay-boundaries-repository-main/2023-10-24/hierarchical_t0p005/municipalities.geojson \
  --output /tmp/new-barangay-boundaries.geojson \
  --sources-output /tmp/new-barangay-boundaries-sources.json
```

Outputs must not exist, and inputs are never overwritten. All 15 codes are
required unless `--allow-subset` is explicitly supplied. Shapely and pyproj are
optional development-only analysis libraries, not new application dependencies;
without them the report says topology was not checked and cannot certify it.

## Historical Overlays

The two existing hazards are grouped as Natural Hazards in the `hazards` pane,
off by default with opacity 0.65. They retain their original native KMZ registration
and limitations. Hazard overlays are not a mutually exclusive physical group.
The four historical physical-characteristic originals requested by V3 are absent;
no placeholder URLs, guessed georeferencing or image-derived polygons are added.
The supported zero-rotation GroundOverlay/LatLonBox KMZ path is ready for future
properly registered inputs, with role `historical_physical_characteristic`, pane
`physical` and an optional shared `exclusive_group`. A general raster engine is
not introduced by this implementation.

## Rebuild After Edits

Rerun `python3 build.py --isolated --offline` after every source/configuration
change, then refresh the browser. Edit `src/data/gis/` and configured source
files, not generated `assets/gis/`, inline page JSON, minified scripts, or
`_site/`. Root `gis/index.html` is a generated mirror and remains unchanged unless
you explicitly use `--sync-gis`; it is not the layout source. If a browser still
shows old data, confirm the server's directory is `_site/` and reload without cache.

Build diagnostics identify skipped malformed features or unavailable optional
layers. Invalid IDs/types and unsafe paths fail configuration validation.
Missing input files or technically unsupported raster registration do not make
other valid layers unavailable. KMZ support extracts bounded PNG overlays with
the understood zero-rotation `LatLonBox` registration. Unsupported transforms
cannot be positioned by the current renderer; no guessed bounds or replacement
approval process makes those rasters available.

## Output and Checks

Only configured generated GIS resources under `assets/gis/` are staged, never
whole raw/research directories. Staging retains explicit page, browser-asset,
and linked-download enumeration, symlink checks, and safe destination cleanup.
The build keeps script-safe JSON, HTML escaping, restricted URLs, structural
geometry validation, bounded archive/image parsing, and per-layer browser errors.

CI builds `_site/` once, tests that exact output with the browser runner and
internal-link checker, and uploads the same directory after the other quality
checks pass. Local focused checks include:

```sh
python3 -m pytest tests/test_staging.py -q
node --test tests/gis-runtime.cjs
node tests/browser/gis-explorer.cjs --fixtures
node tests/browser/gis-explorer.cjs --root "$PWD/_site"
python3 check_i18n.py
```

Browser checks require the project's Node dependencies and Chrome. Controlled
library fixtures test application behavior; they do not certify live map tiles,
geographic accuracy, hazard analysis, or evacuation guidance.
