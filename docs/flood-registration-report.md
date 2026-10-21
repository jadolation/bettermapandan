# Flood Registration Report: V3.2.1

## Decision

Source-reference fallback only. No flood raster, public image viewer, rectified
PNG, GeoTIFF, KML, or KMZ was produced or published. This is not a completed flood
map. No flood extent, parcel category, flood depth, risk grade, or routing advice
is derived. Existing physical and hazard layers are not evidence for this image's
rights or registration.

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

## Registration Assessment

Local research consisted of inspecting the complete supplied raster and its
printed registration evidence. Longitude labels include 120 degrees 25 minutes
12 seconds E, 26 minutes 6 seconds E, 27 minutes E, 27 minutes 54 seconds E, and
28 minutes 48 seconds E. Latitude labels include 16 degrees 2 minutes 6 seconds N,
1 minute 12 seconds N, 0 minutes 18 seconds N, and 15 degrees 59 minutes 24 seconds N.
There are interior cross marks, coordinate labels along the border, a north
arrow, and a lower-left legend. The source is a full poster with embedded
satellite imagery, road/irrigation linework and administrative boundaries, not
a transparent hazard-only raster.

These observations suggest possible distributed graticule controls but do not
verify the grid's construction, datum, projection, or independent positional
accuracy. No independently verified road/river intersections or durable ground
checkpoints were obtained from the available evidence. Municipal bounding-box
corners, facility markers and indicative barangay polygons are not substituted
for control points. No affine fit, warp, residual statistics, bounds, or accuracy
claim is made. Registration stopped at this evidence gate rather than inventing
controls or treating a visual fit as verification. Local research is distinct
from permission to redistribute imagery.

`flood-registration-controls.csv` deliberately contains only the schema header:
zero verified controls and zero independent checkpoints. Blank results are not
zero error. There is no defensible rectification to package through the existing
zero-rotation LatLonBox PNG/KMZ extractor yet.

## Required Before An Overlay

1. Establish artwork and embedded-imagery reuse rights and cite their scope.
2. Verify the source CRS/grid and collect well-distributed measured controls with
   evidence and separate independent checkpoints in the accompanying CSV.
3. Reproduce a justified transformation; record control residuals and independent
   errors separately, including units, CRS, transform, software and parameters.
4. Check center/corners, Angalacan River, Pias/Baloling/Sta. Maria and Primicias
   against independently supported geography; document discrepancies and screenshots.
5. Export a north-up rectified PNG without map furniture. Retain the historical
   imagery with disclosure if hazard-only masking cannot be defended. No naive
   color classification. Package as existing zero-rotation KML LatLonBox KMZ.
6. Change the configured source-reference to that real KMZ only after the above;
   retain default-off, hazards pane, 60% opacity, thematic-rasters exclusion group,
   exact High and Medium source classes, citation and limitations. Use measured
   legend colors only when the overlay exists. Test exact generated manifest,
   staged/synced resources, all locales, mobile and genuine Leaflet.

## Implemented Fallback

The Natural Hazards entry has no geometry or image request, and exposes a direct
official-page citation plus localized explanation. A static source panel retains
the link without JavaScript or Leaflet. The four physical maps, two existing
hazards and future flood overlay share `thematic-rasters`, with existing runtime
checkbox synchronization, in-page opacity retention and no toggle-driven zoom.
Pangasinan wording is provisional UI text requiring maintainer language review,
not an authoritative translation of technical source classifications.

## Verification

- `python3 -m pytest -q`: 525 passed, 19 skipped. The first full-suite run hit
  a 120-second command timeout; the completed run used 360 seconds. Skips are
  reported as skips, not successful source-registration checks.
- `python3 -m pytest tests/test_gis*.py -q`: 242 passed, 19 skipped.
- `node tests/browser/gis-explorer.cjs --fixtures`: 30 controlled runtime cases.
- `node tests/browser/gis-explorer.cjs --root _site`: 12 exact built/minified
  artifact cases. This existing suite uses a controlled Leaflet mock.
- `node tests/browser/gis-markers.cjs --root _site`: genuine Leaflet on all three
  locales at 320, 390 and 1440 pixels; marker centering and resident-reference
  checks pass, including the 12 evacuation listings.
- `node tests/browser/gis-flood.cjs --root _site`: nine combinations of EN/FIL/PAG
  with genuine Leaflet 1.9.4, blocked Leaflet, or disabled JavaScript. Official
  links remain available; no artwork requests, JavaScript errors, or horizontal
  overflow. Keyboard focus reaches the in-layer citation. There is no flood
  checkbox or misleading record-directory action on the source-only entry.
- Browser checks use Chrome `/opt/google/chrome/chrome`, puppeteer-core from
  `/mnt/c/Users/jeydi/AppData/Roaming/npm/node_modules/lighthouse/node_modules/puppeteer-core`,
  and local Leaflet `/tmp/kilo/leaflet.js` plus `/tmp/kilo/leaflet.css`. External
  tiles are deliberately blocked: these are offline renderer/availability checks,
  not live basemap or geographic-accuracy validation.
- Isolated build command:
  `GIS_ESBUILD_BINARY=/home/jeydi/.npm/_npx/beb367dfa21eb3f5/node_modules/@esbuild/linux-x64/bin/esbuild python3 build.py --isolated --offline --sync-gis`.
  It generates 321 pages in `_site` and synchronizes the 291-resource GIS root
  mirror. No normal root build, commit, or deployment is performed.
- `git diff --check` passes. Original source hash remains unchanged.

Screenshots are local test artifacts, not redistributed source-map images:

- `/tmp/kilo/flood-screenshots/flood-en-leaflet.png`
- `/tmp/kilo/flood-screenshots/flood-en-unsupported.png`
- `/tmp/kilo/flood-screenshots/flood-en-no-js.png`
- `/tmp/kilo/flood-screenshots/flood-fil-leaflet.png`
- `/tmp/kilo/flood-screenshots/flood-fil-unsupported.png`
- `/tmp/kilo/flood-screenshots/flood-fil-no-js.png`
- `/tmp/kilo/flood-screenshots/flood-pag-leaflet.png`
- `/tmp/kilo/flood-screenshots/flood-pag-unsupported.png`
- `/tmp/kilo/flood-screenshots/flood-pag-no-js.png`
