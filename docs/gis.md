# GIS Maintainer Workflow

Edit repository data, choose layers, rebuild, and view the map. The maintainer's
selection is sufficient for inclusion; no acknowledgment, approval ledger, pinned
source hash, or GIS-specific environment configuration is required.

## Build and View

Install the project dependencies once, then build from the repository root:

```sh
python3 -m pip install -r requirements.txt
python3 build.py --isolated --offline --sync-gis
python3 -m http.server 8000 --bind 127.0.0.1 --directory _site
```

Open <http://127.0.0.1:8000/gis/>. Filipino and Pangasinan are at `/fil/gis/` and
`/pag/gis/`. The isolated build uses a disposable workspace and exports `_site/`;
it does not replace the checkout's legacy generated page trees. The explicit
`--sync-gis` refreshes only the managed GIS mirror described below.

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
source-reported DPWH project points, all canonical Project References, indicative
barangay boundaries, four historical physical-characteristic KMZ overlays, and
ground-shaking/liquefaction KMZ overlays. Records without supplied valid geometry remain searchable
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
canonical matches. Project records are not expanded into a second below-map
directory. A compact canonical Project Explorer link works without JS; all project
search data and exact links remain in `GIS_RECORDS`. Barangay and facility no-JS
directories remain in collapsed `details` sections with existing DOM IDs.
No canonical coordinates, reference populations or project IDs are changed here.

## Indicative Boundaries

`src/data/gis/barangay_boundaries.geojson` is the small prepared runtime source;
`barangay_boundaries_sources.json` describes raw-source provenance and comparison,
not approval. Both supplied shapefile sets have SHP, SHX, DBF and PRJ components:
geographic `BgySubMuns` and projected UTM zone 51N `PH_Adm4_BgySubMuns`. Their DBFs
do not establish a source vintage; no source date or field verification is invented.

The layer uses `barangay_boundary`, is titled **Barangay Boundaries (Indicative)**,
and remains off by default. Canonical ten-digit PSGC identities, names and
population vintages remain separate from geometry provenance. Source names are
retained; normalization maps source geometry IDs to `provenance.source_record_id`
and source notes to `limitations`.

The candidate extent is about 20.44 km2, whereas historical CLUP text reports
32.91752 km2. This discrepancy is unresolved. Valid polygons do not establish
legal jurisdiction, surveyed accuracy or official territory area. Do not infer
address jurisdiction or precise soil/hazard classes from these boundaries.
The old hierarchical_t0p005 source remains in raw source directories, but its
six-triangle/nine-quadrilateral statistics do not describe replacement geometry.
Detailed raw-source comparison belongs in the descriptive sidecar; independent
field and jurisdictional verification remain unclaimed.

The recorded raw-source comparison measures 15 valid polygons with 985 coordinate
positions and union area 20.4368683561 km2 in EPSG:32651. The geographic source
matches the bundled candidate coordinates exactly. Reprojecting the second raw
source gives only floating-point differences (maximum Hausdorff distance below
0.000001 m). No pair exceeds the report's 1 m2 overlap tolerance and no interior
holes were found. These are source-agreement/topology checks, not independent
positional or legal verification, and they do not resolve missing external
territory. The old byte-faithful extract is retained at
`datasets/GIS/boundaries/legacy_hierarchical_t0p005_mapandan_barangays.geojson`.

## Historical Overlays

The two existing hazards are grouped as Natural Hazards in the `hazards` pane,
off by default with opacity 0.65. They retain their original native KMZ registration
and limitations. Hazard overlays are not a mutually exclusive physical group.
All four original physical posters are present under the V3.1 package's
`sources/physical/`: `elevation.png`, `slope.png`, `soil_classification.png` and
`land_capability.png`. Their printed MPDC preparation date is **2021-12-15**, not
2012. The underlying thematic-data vintage is unknown; older CSV labels do not
establish the posters' source year.

Prepared inputs are `datasets/GIS/physical/prepared/physical-elevation.kmz`,
`physical-slope.kmz`, `physical-soil.kmz` and `physical-land-capability.kmz`.
The existing KMZ loader validates north-up PNG GroundOverlay registration and
emits `assets/gis/physical-*-0.png`, without copying original posters or archives
into the isolated child build. Configuration uses pane `physical`, initial
opacity 0.6, shared `exclusive_group: physical-characteristics`, and off-by-default
visibility. These are historical references, not field measurements or live
safety guidance. Source-pixel legends must match the preparation report; the
land-capability poster's heading says Slope, its visible classes are A/B, and no
geographic Class X extent is invented. Independent controls and residuals are
only claimed where the preparation report actually documents them.

Each `physical-*.source.json` beside the prepared KMZ records original source
path, printed credits and sampled legend RGB. Each `physical-*.registration.json`
records crop, transformation, six fit and six withheld printed-grid crossings,
meter residuals, datum assumption and source-context checks. Withheld internal
grid RMSE is about 0.020 m for elevation/slope, 0.811 m for soil and 1.065 m for
land capability; these tiny grid-fit numbers are not thematic/source accuracy.
Independent OSM road-junction comparisons show approximately 15-93 m offsets;
the preparation does not move the source to erase them. No suspect candidate
boundary was used as a truth mask. White exterior pixels are made transparent,
but some source road/context markings and graticule lines remain.

With current inputs the generated manifest enumerates 89 resources: 85 PNGs
(81 native hazards plus four physical overlays) and four GeoJSONs (roads, places,
DPWH projects, indicative barangay boundaries). The manifest itself is the 90th
managed GIS file. Isolation and staging select these exact resources, never the
original scans, shapefile directories or registration reports.

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

### Runtime weather overlay

“Show weather” adds RainViewer past-radar tiles to the existing Leaflet map and
loads the Open-Meteo area forecast. Radar opacity defaults to 65%; its frame
selector is separate from the hourly forecast selector. All weather times use
12-hour Asia/Manila time (PHT). Weather is opt-in and never fetched during builds.

RainViewer metadata is cached for ten minutes while enabled; forecast data for
one hour. Disabling weather removes tiles and the forecast summary and cancels pending
metadata requests. Radar requests use native zoom 7 with Leaflet overscaling,
so municipal-level zoom does not imply barangay-level precision. Frames older
than one hour are hidden; failed radar requests do not disable the forecast.
Blank radar tiles can indicate missing coverage, not necessarily dry weather.
Provider details: https://www.rainviewer.com/api/weather-maps-api.html.

Test with an existing Chromium executable:

```sh
CHROME_PATH="/path/to/chromium" node tests/browser/gis-weather.cjs --root "$PWD/_site"
```

The test uses actual Leaflet with deterministic weather responses. Set
`WEATHER_LIVE_RADAR=1 WEATHER_VISUAL=1 WEATHER_SCREENSHOTS=/tmp/weather-screens`
to check live radar and capture screenshots; Open-Meteo readings remain fixtures.

#### RainViewer verification (22 October 2026)

The integration matches the official Weather Maps API and Leaflet example:
metadata supplies the host and opaque frame path; PNG tiles use colour 2
(Universal Blue), 256-pixel tiles and native zoom 7. Higher map zooms overscale
those tiles. `1_0` enables smoothing without separate snow colouring.

A direct pixel check of all 13 returned Mapandan frames at z7/x106/y58 found
fully transparent images. The latest frame was also transparent with 512-pixel
images, smoothing disabled, and the latitude/longitude endpoint. Regional z4
and world z0 control tiles contained visible pixels. This establishes an empty
local response at the time of testing, not permanent missing coverage or dry
weather. The coverage mask is not a live station-health check.

The UI inspects loaded tile pixels intersecting the viewport and explicitly
reports transparent views. Browser fixtures test transparent and visible
responses. The optional live check also zooms out and verifies visible regional
radar pixels; live outcomes depend on the provider and weather.

References:
- https://www.rainviewer.com/api/weather-maps-api.html
- https://www.rainviewer.com/api/color-schemes.html
- https://www.rainviewer.com/api/transition-faq.html
- https://github.com/rainviewer/rainviewer-api-example

PAGASA was investigated but no PAGASA integration was added.

Frame replacement now removes the layer from the map before clearing its event
handlers. Reversing that order removed Leaflet's own cleanup listener and left
stale map zoom handlers. The Chromium regression test changes frames, disables
weather, and zooms the map to catch this lifecycle failure.

Radar playback is opt-in through Play radar / Pause radar. It loops the available
past frames, waits for tiles to load, and keeps the 12-hour frame selector in
sync. The delay is at least 1.5 seconds, increasing for views with more tiles to
limit requests. Manual frame selection, map movement, a hidden tab, tile errors
and disabling weather pause playback. Forecast readings appear only in the side
summary; the duplicate Mapandan marker has been removed.
