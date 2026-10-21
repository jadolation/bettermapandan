# Better Mapandan GIS — V3.2 Flood Susceptibility Layer Addendum

**Prepared:** 21 October 2026  
**Status:** Implementation-ready specification and original source image. **Not georeferenced, deployed, or integrated into the user's local repository.**  
**Base:** `GIS_IMPLEMENTATION_PLAN_V3_1_BASE.md` remains in effect for all 15 barangays, four physical-characteristics maps, existing ground-shaking and liquefaction layers, facilities, roads, and DPWH records.

## 1. Decision

Add **Flood Susceptibility (Municipal Map)** as an **additional** Natural Hazards layer to the existing Python build + vanilla JS/Leaflet Explorer. The user confirms the map's red/orange areas refer to flooding. The artwork legend identifies **High** (red) and **Medium** (orange); absence of colored fill does *not* prove absence of flood hazard.

The supplied image `sources/flood/Mapandan-Hazard-Map-scaled.jpeg` is the immutable source. It is a 2048 × 1448-pixel municipal poster with satellite imagery, a red dashed municipal boundary, red dashed/black administrative and road linework, blue waterways, susceptibility shading, printed coordinate/grid references, and a legend inset at lower left. Source organization, survey date, hazard model, return period, and publication date are **not verified from this JPEG**; do not invent them. "Municipal map provided by maintainer" is a neutral provisional attribution pending identification of the issuing office and original publication.

## 2. No new architecture

- Retain existing `src/data/gis/layers.json`, `_build/gis_sources.py`, `_build/gis_preview.py`, `assets/gis-map.js`, `assets/css/map.css`, existing renderer panes and opacity controls, project adapters, EN/FIL/PAG localization, and `_site` builds.
- Do not introduce publication approvals, a second site mode, user accounts, backend GIS services, or image-analysis claims.
- Do not replace either PHIVOLCS ground shaking or liquefaction. This is an independent, source-specific flood-susceptibility layer.
- **Do not simply feed this JPEG to `L.imageOverlay` with the municipal bounding rectangle**. The image includes a poster legend and uses cartographic registration requiring verification.

## 3. Raster preparation and geographic registration

1. Copy the unchanged original to `datasets/GIS/flood/originals/Mapandan-Hazard-Map-scaled.jpeg` (or equivalent source-managed directory).
2. In QGIS, inspect the map frame, corner/graticule labels, possible north orientation and the source's CRS. Establish ground-control points using actual longitude/latitude grid intersections and separately verified locations such as durable road/river intersections; include well-distributed points and retain independent check points. **Printed labels are not enough without verifying how the grid was constructed.**
3. Rectify/warp the image to a suitable georeferenced GeoTIFF intermediate; verify registration on OSM and against the candidate Mapandan barangay boundaries and recognizable river/road geography. Note source/image residual errors and independent horizontal deviations. Do not accept merely because colors look attractive.
4. Export a north-up, correctly positioned transparent RGBA PNG (or supported tiled/raster format). Cut off map furniture: header labels, legend, north arrow, scale bar, margin, black frame, and all non-geographic parts. Where practical, use an alpha mask to preserve **only high and medium thematic susceptibility shading** and remove embedded satellite/road text; because thematic colors overlap background colors, **do not use unchecked naive color thresholding**. Manual QA and a visual comparison with the original are required. If clean hazard-only masking is not achievable, a well-registered *historical map image* with an opacity control is acceptable, provided its embedded imagery and linework are clearly described. Do not promise data extraction or pixel classification.
5. Prefer a **source-accurate thematic overlay** with transparent other areas. Do not remove meaningful colored hazard areas. Use the original map as an openable documentary reference outside the map canvas.
6. Check the rectified raster at map center, all corners, along Angalacan River, Pias/Baloling/Sta. Maria, and southeast near Primicias. Verify no north/east mirroring, rotation mistakes or stretch errors. Polygon borders and facility markers must remain on top and clickable.
7. Supply measured/verified bounds as `[south, west, north, east]` for Leaflet (source longitude/latitude remains `[lon, lat]` elsewhere). No illustrative coordinates should ship as actual registration.
8. If georeferencing cannot be defended, add a **Source Map (image viewer)** reference entry with the original JPEG and a precise note; do not publish a misregistered geographic overlay.

## 4. Integrate with build and runtime

- Proposed ID: `flood-susceptibility`; English title: **Flood Susceptibility (Municipal Map)**; type: existing supported raster image overlay pipeline, e.g. a KML GroundOverlay KMZ after rectification, or a prepared rectified-PNG manifest adapter. The existing `layers.json` input schema lists `geojson`, `records`, `dpwh`, `kmz`: **do not insert an invented `raster` input type until implementing and testing its loader**.
- Set `enabled: true`, `visible_by_default: false`, `pane: "hazard"`, category **Natural Hazards**, and default opacity about 0.6. Preserve the user's last session opacity while toggling.
- Include source metadata: title, issuing organization if established, original image reference, datedness status (`date unknown` unless documented), registration method/check summary, `location_precision: approximate_historical_map`, classification limitations, and optional source URL only when actually verified.
- Legend entries are **High flood susceptibility** (red) and **Medium flood susceptibility** (orange). Do not introduce "Low", "No risk", depths, probabilities, or return periods without source support. Legend and citation belong **outside** the georeferenced image map pane. If original poster is retained as documentary layer, note that the poster has its own legend inset.
- Keep other thematic rasters off when flood is first enabled (or provide explicit one-thematic-raster-at-a-time selection) to avoid uninterpretable color stacking; do **not** silently hide user choices without reflecting UI state.
- Use existing ordered panes: basemap → physical maps → flood and other hazard rasters → indicative barangay boundaries → infrastructure → facilities/selected items. Hazard rasters must use `pointer-events: none` or equivalent click-through behavior.
- Add EN/FIL/PAG display labels and explanatory text; don't fabricate authoritative Pangasinan translations—have maintainer check them. Match source class terms across locales.
- Ensure `_build/staging.py` and optional `_build/gis_sync.py` copy/allowlist the new emitted image/KMZ resources via the generated manifest. Use canonical asset URLs so all three routes work.

### Example `layers.json` record (conceptual — use actual adapter/source filename)

```json
{
  "id": "flood-susceptibility",
  "title": {"en": "Flood Susceptibility (Municipal Map)", "fil": "Flood Susceptibility (Municipal Map)", "pag": "Flood Susceptibility (Municipal Map)"},
  "type": "kmz",
  "source": "datasets/GIS/flood/flood_susceptibility_registered.kmz",
  "enabled": true,
  "visible_by_default": false,
  "pane": "hazard",
  "semantic_role": "flood_susceptibility_reference",
  "source_label": "Municipal flood susceptibility map supplied by maintainer; originating office and date not yet confirmed",
  "precision": "Historically mapped, indicative; georeferencing accuracy must be checked",
  "limitations": "Not real-time; unshaded areas are not certified flood-free; not for emergency response or parcel-level decisions"
}
```

The `registered.kmz` above **does not exist in this package**. It must be produced from verified georeferencing. The exact keys (including category, legend, opacity) must match the actual local schema; extend it only where necessary. Any placeholder translations or metadata in this example are **not publication-ready**.

## 5. UX acceptance checklist

- Flood toggle appears in **Natural Hazards**, clearly separate from liquefaction and ground shaking; unchecked by default.
- Toggle loads registered imagery (not the full uncropped poster), changes visibility without changing zoom, and shows loading/error feedback.
- Legend correctly shows exactly **High** (red) and **Medium** (orange); no green or no-risk class invented; attribution and source date status visible.
- Opacity slider updates without request reload; base map remains legible at its chosen opacity.
- Barangays remain clickable and searchable. Selecting polygon reveals source/reference statistics but does **not** infer individual parcel flood category from pixel colors.
- Original full image can be opened as a source reference outside map canvas.
- If georeferencing is unsatisfactory, source viewer appears instead of falsely aligned map layer.
- Flood source, four V3.1 physical rasters, two existing hazards, facilities and roads coexist correctly.
- Works on `/gis/`, `/fil/gis/`, `/pag/gis/`, mobile and keyboard; generates the same `_site` used for tests/deployment.
- No new permissions or approval ledger; preserve routine safe rendering and path/geometry validation.

## 6. Tests and implementation order

1. Confirm title/legend and metadata with maintainer; label date/office unknown if necessary.
2. Make QGIS georeferenced intermediate, inspect control points, capture registration evidence screenshots and deviations; produce transparent raster and actual bounds.
3. Package as supported KMZ or implement minimally compatible prepared-raster adapter; write generated asset manifest.
4. Add layer config, locale strings, legend and opacity UI. Explicitly maintain layer order and click-through.
5. Run existing Python, JS, Chrome/browser tests, `python build.py --isolated --offline`; then inspect `/gis/`, `/fil/gis/`, `/pag/gis/` against the original source screenshot at multiple zooms.
6. Record changed files, the *measured* alignment issues, the layer's actual attribution/date status, tests actually run, and any remaining blocker. Do not assert completed integration until it is served in browser.

## 7. Non-goals and publication wording

Do not classify individual buildings or residents as high-risk from poster pixels, compute affected population or flood height, or imply the map is real-time. Display: **"Historical municipal flood-susceptibility reference. High and Medium are classifications shown on the source map. Uncolored areas are not necessarily flood-free. Confirm current conditions and official advisories with local disaster authorities."**

**Completion is a visually aligned, transparent/legible flood layer backed by actual source geometry and working in the current local build. This package only provides the original image and the integration specification.**
