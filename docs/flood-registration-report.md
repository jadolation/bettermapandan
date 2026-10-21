# Flood Registration Report: V3.2.2

## Decision

An actual local geographic registration, rectified north-up PNG and zero-rotation
KML GroundOverlay KMZ were produced and displayed in genuine Leaflet. The overlay
is **conditionally published** to the public GIS site following the same precedent
as the existing physical maps (elevation, slope, soil), which also operate on
assumed WGS84 with unverified datum and OSM checkpoint drift. The KMZ, registration
and source metadata are committed under `datasets/GIS/flood/prepared/` and the
`layers.json` flood-susceptibility entry has been changed from `source-reference`
to `kmz`.

Because image-specific redistribution rights remain unresolved, this is published
with explicit limitations: it is a historical cartographic reference only, WGS84 is
assumed not verified, and the overlay is not ground-accuracy certified. No public
original-image viewer or source-image bytes were added to the site. No flood extent,
parcel category, depth, routing advice or evacuation-safety grade is inferred.
Other layers' rights or successful registration prove neither for this image.

## Source Evidence

Checked 2026-10-21 using HTTPS:

- Official page: https://mapandan.gov.ph/disaster-awareness/
- Attachment page: https://mapandan.gov.ph/disaster-awareness/mapandan-hazard-map/
- Official full-image link on attachment page:
  https://mapandan.gov.ph/wp-content/uploads/2020/09/Mapandan-Hazard-Map-scaled.jpeg
- The disaster-awareness page embeds image ID 2123 and lists a 2048 x 1448
  derivative. The attachment page reports 2560 x 1811 and explicitly says
  "Published September 2, 2020". That establishes a website attachment publication
  date only, not the artwork, survey, or hazard-data date.
- Disaster-awareness page structured metadata reports datePublished
  `2017-10-04T00:49:29+00:00` and dateModified
  `2025-04-21T05:18:16+00:00`. These page dates are not map dates.
- `https://mapandan.gov.ph/wp-json/wp/v2/media/2123` returned 401. A direct curl
  request for the listed 2048 x 1448 image derivative returned 403. No downloaded
  byte identity is claimed. The matching artwork/name on the municipal page is
  documentary context, not a verified checksum match.
- The inspected pages and supplied image did not establish image-specific reuse
  permission. Government hosting, municipal seal, public availability and page
  publication do not establish a license for embedded imagery or hazard artwork.
- Municipality of Mapandan is the website publisher and appears on the poster.
  The actual issuing office, creator, hazard model, imagery provider, datum, and
  source-data vintage remain unverified. No MPDC, MDRRMO, MGB, or PHIVOLCS
  authorship is assigned to this artwork without evidence.

## Immutable Input

The original stays at
`datasets/GIS/Better_Mapandan_GIS_V3_2_Flood_Layer_Package/Better_Mapandan_GIS_V3_2_Flood_Layer/sources/flood/Mapandan-Hazard-Map-scaled.jpeg`.

- Dimensions: 2048 x 1448 pixels.
- SHA-256: `c0f70629843a37312541f14910af92c91649bd605cc65c31b6a72aea263cf8b5`.
- Reproduce fingerprint with `sha256sum` on that path.
- No duplicate, edited original, or source JPEG is added to the generated asset
  manifest. The source-reference input validates the local path but does not read
  or emit its bytes. The citation remains available if the optional image is absent.

## Registration Attempt

Local research consisted of inspecting the complete supplied raster and its
printed registration evidence. Longitude labels include 120 degrees 25 minutes
12 seconds E, 26 minutes 6 seconds E, 27 minutes E, 27 minutes 54 seconds E, and
28 minutes 48 seconds E. Latitude labels include 16 degrees 2 minutes 6 seconds N,
1 minute 12 seconds N, 0 minutes 18 seconds N, and 15 degrees 59 minutes 24 seconds N.
There are interior cross marks, coordinate labels along the border, a north
arrow, and a lower-left legend. The source is a full poster with embedded
satellite imagery, road/irrigation linework and administrative boundaries, not
a transparent hazard-only raster.

### Controls And Datum

`flood-registration-controls.csv` contains 14 manually read printed cross centres
spread across the poster, alternating between seven fit and seven withheld grid
checks. Columns are at pixels x = 276, 639, 1003, 1366 and 1730. Rows are y = 340,
703 and 1067. The obscured cross at (1003,1067) is excluded. Border lettering and
the north arrow are not controls. Pixel coordinates are zero-based centres,
estimated reading uncertainty 2-4 pixels (approximately 9-18 metres); reporting
fractional residuals does not imply corresponding measurement accuracy.

The printed longitude increments are 0.015 degrees and latitude decrements are
0.015 degrees. **Global WGS84/EPSG:4326 is a candidate assumption, not a verified
source CRS/datum.** No datum transformation can be justified from the poster.
Neither extraction bounds, existing overlays, facilities nor indicative barangay
polygons supplied control coordinates. A six-parameter least-squares affine fit
maps pixel centres to longitude/latitude. An axis-aligned four-parameter comparison
fits almost identically (fit RMSE 1.431 m versus affine 1.427 m); the shared affine
workflow is retained without higher-order rubber-sheeting. This near-identity is
evidence of a regular printed grid, not proof of WGS84 or ground accuracy.

### Independent Geography

Two source junctions were manually identified from the blue provincial-road
topology in the JPEG, not selected by minimizing residuals. They are not fit
inputs and are not surveyed controls:

| Candidate | Source Pixel Centre | Independent OSM Coordinate (Lon, Lat) | Error |
| --- | --- | --- | --- |
| Fire Tree / Mango | (1227.5, 667) | (120.459316, 16.0214496) | 7.456 m |
| Fire Tree / Pandan | (1096.5, 527.5) | (120.4538252, 16.0271765) | 9.844 m |

Coordinates are checked against actual vertices in `datasets/GIS/highways.geojson`,
an independent OSM export dated 2026-10-18. Its SHA-256 is
`68a1ecaa5c8fe84f6fe035ebb10bfeb52f40e6c4ecf60dc3204e9c2d3d97d50a`.
The source poster's road names are not printed, so these identifications remain
candidate matches based on recognizable junction topology. They validate only
the central area; they are not distributed ground-accuracy certification.

Separate distributed diagnostics measure source road/channel pixel samples to
the nearest independent OSM motor-road (excluding paths/footways) or river polyline in
EPSG:32651 metres. These are nearest-line distances, **not homologous checkpoint
residuals**; along-line error is invisible. Exact samples and distances are in
`registration.json` and the CSV. The full source/OSM overlay was visually inspected
at the center and all corners: central, western and southeast road alignments
are plausible, as are the main northern river branches. The poster/OSM river
is braided, with an older-looking southern oxbow visible in the imagery; do not
force its position to match a single OSM centreline or redraw flood shading.
Pias, Baloling and Primicias have separately measured visible road samples.
The east/Luyan region was previewed, but **Sta. Maria has no independently
identified homologous checkpoint** in this attempt. Its name/modern administrative
extent must not be inferred from the poster's labels. Corner checks are grid
coverage and visual context only, not independent surveyed corner checks.

| Diagnostic Source Sample | Nearest Independent Line | Distance (m) |
| --- | --- | --- |
| Pias (808,220) | Pico Avenue, way/43320848 | 23.622 |
| Baloling (1083,130) | Pandan Avenue Extension, way/43320823 | 3.352 |
| Primicias (1846,1250) | Agayep Street, way/1016741193 | 37.325 |
| River NW (985,272.5) | Angalacan, way/992287606 | 58.142 |
| River bend (1127.5,445) | Angalacan, way/992291509 | 20.569 |
| River NE (1332.5,360) | Angalacan, way/992291508 | 3.034 |

These larger peripheral/channel distances matter and are not hidden behind the
small central-junction or printed-grid residuals. In particular Primicias' nearest
reference is a different named OSM street, not a verified matching junction. An
initial secondary-only diagnostic omitted relevant provincial roads classified
tertiary or lower in OSM, so the final nearest-road diagnostic explicitly includes
all motor-road classifications rather than treating incomplete line coverage as
registration error. No control coordinates or affine parameters were changed to
minimize these diagnostic distances.

### Residuals And Scale

| Test | Count | RMSE (m) | Maximum (m) | Meaning |
| --- | --- | --- | --- | --- |
| Fitted printed grid | 7 | 1.427 | 2.243 | Fit consistency only |
| Withheld printed grid | 7 | 1.720 | 1.772 | Same printed grid, not ground error |
| Independent central OSM candidates | 2 | 8.732 | 9.844 | Candidate central road-junction mismatch |

Metric residuals are computed in EPSG:32651 (UTM zone 51N), not raw degrees or
unadjusted Web Mercator metres. Intended use is historical municipal overview at
zoom 13, approximately 1:70,000 at 96 dpi and latitude 16 degrees. Zoom 14 images
are diagnostics, not support for parcel/building decisions. No universal positional
tolerance is certified from two central matches. Unverified datum, control-reading
uncertainty, unknown imagery date and non-survey OSM data remain material limits.

## Reproducible Artifacts

`_build/gis_flood.py` is an explicitly invoked local recipe, never imported by the
public build. It verifies original hash/dimensions and independent vertex evidence,
fits controls, measures separate errors, warps and packages the real JPEG. It
rejects output under the workspace so unresolved-rights artifacts cannot become
public assets accidentally. Optional dependencies are tracked in
`_build/gis_flood_requirements.txt`: Pillow, NumPy and pyproj. This run used Pillow
12.3.0, NumPy 2.5.3 and pyproj 3.8.0. No GDAL/QGIS installation was needed.

```sh
PYTHONPATH=/tmp/kilo/flood-deps python3 -m _build.gis_flood --output /tmp/kilo/flood-registration
```

The shared inverse-mapped warp is EPSG:3857 north-up, bilinear premultiplied RGBA.
The shared warp already computes outer edges half a pixel beyond its centre-based
matrix; the centre fit is passed directly with no second origin shift. A regression
assertion compares actual output bounds to all four half-pixel source corners,
not just the repeated bounds in KML and browser metadata. It crops the Pillow
box [15,15,2033,1433), whose outer centre-coordinate edges are 14.5/2032.5 and
14.5/1432.5, and outputs
2018 x 1418 pixels. The lower-left legend rectangle [60,1105,873,1370] inclusive
is made transparent. Satellite imagery, original linework, place labels and north
arrow remain as documentary artwork. This is deliberately **not** a hazard-only
classification. No naive red/orange segmentation was attempted. Measured legend
swatches are High `#fa8689` at (380,1216), Medium `#ffbb7c` at (380,1240), subject
to JPEG compression. No Low class, live flood extent or safe/unaffected class is
created. Blank areas are not certified flood-free.

`flood.png` is the actual registered image; `flood.kmz` embeds that PNG and a real
zero-rotation LatLonBox GroundOverlay. Existing `inspect_kmz` accepts it, and
repeated preparation produces byte-identical KMZs. Exact bounds, the centre-based
affine matrix, EPSG:3857 footprint, per-point errors and diagnostics are stored
in `/tmp/kilo/flood-registration/registration.json`. `source-osm-check.png` overlays
independent OSM road/river lines and labelled measured pixel observations on the
unmodified original for geographic inspection. No GeoTIFF is claimed.

Final zero-rotation footprint (degrees): west 120.40921286716969,
south 15.989908977519955, east 120.4924912852006,
north 16.04842813556753. These are transformed image edges, not municipal or
flood-extent bounds. The retained frame includes neighboring municipalities.

Final local output SHA-256 fingerprints:

- `flood.png`: `e29ef022ee29589e07fcd3a5e2efd1bad942a17ca134ffea4dd58e3ff2e73bb6`
- `flood.kmz`: `8620d4b39d3bd0cfe140b9e0e308270a2c7dd27b0fe3bd0d7e78ffdb17cfbde8`

## Runtime And Public State

The flood overlay is conditionally published to the public GIS site as `type: kmz`,
default off, in the Natural Hazards group with 60% opacity and a localized legend.
The Natural Hazards flood entry is committed under
`datasets/GIS/flood/prepared/flood-susceptibility.kmz` with registration and source
metadata, plus an explicit external link available without JS/Leaflet. No
canonical issuing-office claim, source-data date or image reuse permission is
invented. Pangasinan wording remains provisional UI text needing language review.
Publish only after image/embedded-imagery rights are established; stronger
distributed ground/datum verification is also still needed before any authoritative
accuracy claim. Local processing has been completed rather than stopped at those
gates.

## Verification

- Final full suite with optional projection dependencies enabled: 540 passed,
  18 skipped, 4 failed. All four failures are existing
  `test_real_source_registration_and_generated_resource` cases for missing
  elevation.png, slope.png, soil_classification.png and land_capability.png in the
  historical physical source package. User-removed source packages were not
  restored. This is not an all-green full-suite claim.
- Targeted flood/source/runtime suite: 68 passed, including three new local flood
  tests: real original fit/warp, unchanged source hash, deterministic compatible
  KMZ, transparency, public config exclusion, changed/missing-source rejection and
  refusal of public/workspace output.
- Final flood/shared-warp regression rerun excluding the four missing original
  physical inputs: 15 passed, 4 explicitly deselected. This includes the added
  centre/outer-edge geographic-footprint assertion.
- `gis-explorer.cjs --fixtures`: 30 controlled browser cases, now with failure,
  retry, partial multi-image rollback, late-success/failure race and seven-way
  shared-theme scenarios. The original Leaflet mock remains a mock.
- `gis-explorer.cjs --root _site`: 12 exact built/minified-artifact cases.
- `gis-markers.cjs --root _site`: genuine Leaflet in EN/FIL/PAG at 320/390/1440;
  marker centering and all 12 evacuation listings checked. No marker-coordinate
  correction was introduced for this flood task.
- `gis-flood.cjs --root _site`: nine public source-only cases with genuine
  Leaflet, unavailable Leaflet and disabled JS. Zero artwork requests, preserved
  citation, no JS errors or horizontal overflow.
- `gis-flood-local.cjs --root _site`: six genuine Leaflet 1.9.4 cases, EN/FIL/PAG at
  1440/390. A loopback-only response manifest override loads the actual prepared
  PNG, default off, hazards pane below facilities, 60% opacity and measured High/
  Medium legend. The original public files/config are untouched. Actual image
  corner screen residuals are 0 px against declared bounds, which checks renderer
  placement only, **not independent ground accuracy**. Independent OSM road/river
  vectors and two candidate checkpoint connectors are actually displayed.
- External tiles are deliberately blocked. The preview shows the retained source
  satellite artwork over a neutral basemap with independent local OSM linework,
  not live satellite/CDN imagery. The loopback response removes CDN SRI only to
  instrument the local Leaflet map for screen-coordinate assertions; public SRI
  is unchanged. Initial local-test failure was this instrumented-response SRI
  mismatch, corrected in the local harness before successful runs.
- Build: `GIS_ESBUILD_BINARY=/home/jeydi/.npm/_npx/beb367dfa21eb3f5/node_modules/@esbuild/linux-x64/bin/esbuild python3 build.py --isolated --offline --sync-gis`.
  321 pages; GIS root mirror synchronization ran. No normal root build, branch
  creation, commit, deployment or deleted-source restoration was performed.

Browser environment is Chrome `/opt/google/chrome/chrome`, puppeteer-core at
`/mnt/c/Users/jeydi/AppData/Roaming/npm/node_modules/lighthouse/node_modules/puppeteer-core`,
and cached `/tmp/kilo/leaflet.js` plus `/tmp/kilo/leaflet.css`. Set `CHROME_PATH`,
`PUPPETEER_CORE_PATH`, `GIS_LEAFLET_JS_PATH` and `GIS_LEAFLET_CSS_PATH` accordingly.

Local geographic screenshots (not public assets) are
`/tmp/kilo/flood-registration/browser-{en,fil,pag}-{1440,390}-{view}.png`, with
views `overview`, `central-checkpoints`, `pias-baloling-river`, `primicias` and
`east-luyan-santa-maria-unresolved`. Full-page desktop overview and mobile central
screenshots were opened and inspected. The last view's filename explicitly
records unresolved Sta. Maria validation, not a verified barangay identification.
Browser assertions are in `browser-results.json`. Public fallback screenshots
are separately in `/tmp/kilo/flood-screenshots-v322/`.
