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

Supported input types are `geojson`, `records`, and `kmz`. Paths must stay within
`src/data/` or `datasets/GIS/`; external URLs, traversal, and unsafe symlinks are
not inputs. `source_url` is optional provenance, not a URL to fetch during a
build. Use optional `source_label`, `attribution`, `source_date`, `precision`,
and `limitations` for honest source/precision text.

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

The initial configuration includes facilities, roads, places, barangay reference
records, canonical project records, and supported ground-shaking/liquefaction
KMZ overlays. Barangays and projects without supplied geometry remain searchable
nonspatial records; project links use canonical IDs. No points are invented.
Approximate extraction bounds are not administrative boundaries. Experimental
traced outlines, label anchors, and color-segmented polygons are not selected;
their research originals and historical V2 handoff files remain unchanged.

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
