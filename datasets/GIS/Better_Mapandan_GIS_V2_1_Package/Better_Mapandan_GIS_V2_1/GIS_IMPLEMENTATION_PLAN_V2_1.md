# Better Mapandan GIS — Implementation Specification V2.1

**Date:** 19 October 2026  
**Repository:** `jadolation/bettermapandan` · working branch `GIS`  
**Status:** Revised specification based on the maintainer-reported corrective implementation; this document does not independently certify the latest branch, review decisions, or public layers.  
**Supersedes:** `GIS_IMPLEMENTATION_PLAN_V2.md` for forward implementation. Historical V2 extraction remains traceable; no candidate geometries are approved by this document.  
**Companion:** `AGENTS.md` in this handoff; install authoritative instructions at repository root after policy reconciliation.

## 1. Current reported baseline and verification

The maintainer reports the following completed implementation. **Confirm against the target commit before further development; these are reported outcomes, not independently re-executed tests.**

| Capability | Maintainer-reported status | Implementation location / verification target |
|---|---|---|
| Evidence-backed, fail-closed facility publication | Implemented; all 16 candidates remain unpublished | `_build/gis.py`, build tests, staged output |
| No internal review history in public payload | Implemented | `_build/gis.py`, output inspection |
| HTML-script-safe JSON embedding | Implemented | GIS HTML generation and injection regression |
| OSM map initializes; co-located candidates share popups without shifting coordinates | Implemented foundation | GIS JS; browser smoke test outstanding |
| Accessible static barangay and approved-facility directories | Implemented | generated HTML; no-JS tests |
| UI no longer claims unsupported layers/16 verified facilities | Implemented | generated pages and locales |
| EN/FIL/PAG GIS UI and precision labels | Implemented foundation | localization checks |
| Allowlisted `_site` publication artifact | Implemented | `_build/staging.py`, pages workflow |
| Typed generalized layer registry, roads/places, hazard overlays, polygon geography | Not implemented | future scope |
| Interactive search/filter/selected-feature workspace | Not implemented | future scope |
| Mandatory production test-to-deploy dependency | Outstanding | GitHub Actions workflows |

**Reported verification:** 367 Python tests passed; 9 JavaScript runtime tests passed; JS syntax and locale parity passed; isolated full build/staging passed; 321 generated pages (107 per locale); 20,215 internal references with zero missing; 43 approved audit downloads preserved; 1,195 byte-identical staged files across repeated staging. **Not performed:** live tile/CDN rendering, real-browser visual/accessibility checks. **Known pre-existing issues:** 36 broader lint diagnostics outside corrective scope. Re-run checks and record exact commit, commands, versions and output before treating figures as current.

### Safety baseline

- All 16 facility candidate records remain **unpublished** until separately reviewed, evidenced, and approved; never auto-publish all 16 for P1.
- Barangay GeoJSON still uses `geometry: null` unless properly approved polygon data has since been introduced.
- Prior geometry extractions (`*_CANDIDATE*`, `*_UNVALIDATED*`) are research-only, not legitimate exposure input, centroids, surveyed borders, or clickable public polygons.
- Source data, approved derivative, and published artifact remain distinct.

## 2. Responsibility and authority

| Role | Can do | Cannot do unilaterally |
|---|---|---|
| Research/data extraction agent | Transcribe source claims, attach hashes/provenance, flag conflicts | Declare geometry or a location verified |
| Data processing/GIS engineer | Produce candidate transforms, code loaders, tests, QGIS QA reports | Approve publication, rights, or safety suitability |
| Independent geographic/data reviewer | Evaluate original evidence, independent checkpoints, positional uncertainty, source reconciliation | Infer redistribution rights without a rights decision |
| Rights reviewer/authorized owner | Document legal basis for display, download, adaptation, attribution | Certify geography without technical QA |
| Publication approver (designated human) | Approve **specific immutable derivative + exact claims + intended scale/use** after reviews | Blanket-approve source revisions or future bytes |
| Release automation | Compare immutable approved manifest with staged bits and publish on passed gates | Grant missing approvals |

Separate approvals for **identity**, **position**, **use/designation**, **rights**, and **publication**. A `source_verified` source flag cannot be promoted into any other state by default. When authorization or responsible reviewer identities are missing, block publishing.

## 3. Binding approved-layer contract

Maintain a reviewable private source registry, derivative registry, and approvals ledger (suggest `src/data/gis/registry/` for published-safe metadata, `datasets/GIS/review/` for internal decisions). A published manifest is mechanically derived, never self-authorizing. Suggested paths must be reconciled with `_build/gis.py` and `_build/staging.py` before code changes; do **not** create `_build/gis/` next to `_build/gis.py` without an intentional migration.

The approved-layer record MUST identify:

1. Source `source_id`, provider, original URL/reference, source date/version/scenario and SHA-256 of original bytes.
2. Allowed usage, redistribution and derivative rights **with evidence** (rights reviewer/decision, date, attribution conditions).
3. Derivative ID, exact SHA-256/size, format, bounds, source CRS, web CRS, precision, transformation/processing method, tool versions.
4. For classified raster/vector data: source legend, class codes/meanings, nodata/unknown handling, color mapping, source scenario and analytical limitations.
5. For image georeferencing: calibration GCPs, transformation, residuals **and independent checkpoints not used for fitting**, checkpoint errors, spatial distribution, map scale, intended display zoom/scale and QA decision.
6. For vector: geometry validity, topology/coverage conditions, canonical IDs (PSGC where applicable), and spatial uncertainty.
7. A designated human reviewer, date, evidence IDs, approval purpose, exact public claims/labels, limits and release status.
8. Available runtime renderer and published URL confirmed to resolve in the staged `_site` artifact.

**Invalidation:** any change to original source hash, derivative bytes/hash, bounds, CRS, registration, legend/classes, scenario/date, precision, approved claims, intended use/scale, license basis, or open blocking issue **invalidates prior publication approval**. Reapproval is explicit; no silent metadata edits.

Illustrative machine-checkable approval (example only, never interpret as a real approval):

```json
{
  "layer_id": "historic-slope-2012",
  "state": "candidate",
  "source_id": "MPDC-SLOPE-2012",
  "source_sha256": "REPLACE_WITH_REAL_SHA256",
  "derivative_sha256": "REPLACE_WITH_REAL_SHA256",
  "geometry_type": "raster-image-overlay",
  "source_crs": "unknown_pending_review",
  "web_crs": "EPSG:4326",
  "bounds": null,
  "legend_version": "historical-2012",
  "rights_decision": "pending",
  "independent_checkpoint_report": null,
  "technical_review": "pending",
  "publication_approval": "pending",
  "approved_claims": [],
  "public_url": null
}
```

No `approved` value may appear merely because a candidate path exists. CI checks the full binding against **real current bytes**, approval ledger, schema, and rendered interface. Any missing requirement blocks export. The example contains placeholders and is deliberately unpublishable.

## 4. Deployment and CI release contract

Set a **blocking** dependency chain: source/schema tests → GIS data/approval tests → Python integration build → JavaScript/runtime tests → headless real-browser smoke and accessibility checks → staging integrity/allowlist/security scan → deployment of the **same verified `_site` artifact**. PR checks and production release should both run the required gates. Ensure a failed gate prevents publication; report external-tile/CDN outages separately from application JS errors. Keep artifacts/hash manifests for release audit.

Tests must assert: 0 unapproved facility markers AND no forbidden facility payload; 15 barangay reference entries (independent of polygon availability); script-injection strings inert; exact output paths and no research/reviewer files; manifest truth vs actual assets/renderer; rejected/changed derivative SHA blocked; unsupported/unknown CRS blocked; source/license missing blocked; missing/changed legend blocked; independent checkpoints required for registered layers; no synthesized polygons from text anchors; accessible no-JS directories and translations; map/list and controls in Playwright. Capture screenshot diffs without making pixel-perfect snapshots the sole pass criterion.

## 5. Engineering work packages (remaining)

| Phase | Scope | Release acceptance |
|---|---|---|
| P0.1 reconcile policy/baseline | Root-scoped `AGENTS.md`, old `datasets/GIS/AGENTS.md` existence/conflict, current `_build/gis.py`/`_build/staging.py`, tests | One explicit authority; no outdated assertions |
| P0.2 gate tests | CI dependencies and Playwright, approved-layer schema and checksums | Intentional failing tests block deployment |
| P1 GIS workspace | Search/filter, list↔map interaction, responsive details, focus management | Works with **zero** approved facilities; no broken toggles |
| P2 map asset engine | Typed manifest registry, approved roads/places if rights+validation pass; user-friendly unavailable states | All toggles backed by staged files and tested loaders |
| P3 source catalog | Six-map historical facts, exact legends, source vintages, 15 elevation rows with reviewed PSGC crosswalk | Reference info may be displayed without geometry claims |
| P4 first approved overlay | Prefer historical slope **only if** source/rights, georef independent QA, derivative hash, legend and publication signature pass | One end-to-end verified layer; otherwise keep disabled |
| P5 polygons + projects | Reviewable historical municipal/barangay cartography and spatial project links | No legally authoritative boundary or precise point claims unless supported |
| P6 hazards/exposure/live | Native KMZ verification, separate poster vintage, authorized raster/WMS, scenario-specific analysis | Independent source review, fit for intended scale/use, safety checks |

**Suggested first layer is conditional:** if historical slope rights/accuracy are not resolved, select a simpler permissible layer (e.g. reviewed road segments) rather than weakening approval criteria.

## Appendix A. Six-map source inventory and extractable classes

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

## Appendix B. Extracted nonspatial Mapandan reference facts

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


## Appendix C. Research artifact mapping and limitations

`data/mapandan_gis_extracted_reference.json`, `data/mapandan_barangay_elevation_reference.csv`, `data/mapandan_gis_quality_flags.csv` are **unreviewed source transcriptions** until source crosswalk and editorial decisions are complete. `data/municipality_outline_CANDIDATE.geojson`, `data/barangay_LABEL_ANCHORS_UNVALIDATED.geojson`, `data/general_slope_UNVALIDATED_color_polygons.geojson`, `data/land_capability_UNVALIDATED_color_polygons.geojson` and `previews/boundary_trace_preview.png` are **staging-only**. Do not copy these files into `_site` without a valid independent approval under Section 3; label anchors must never become centroids/routing endpoints. Original six images are **not** included in this v2.1 handoff; recover them from the approved source/archive and hash them there.

Unresolved anomalies to preserve: soil-area class total 2,631.981 ha versus stated 2,132.704 ha; land-capability class areas 2,132.143 ha versus MPDC municipal area 3,291.752 ha; historical 2023 RHU population 43,722 versus separately published 2024 PSA population 38,228; historical longitude prose conflict; liquefaction `liq_2024...kmz` filename versus 2025 poster caption; purported 2012 date versus image print metadata. These are **review flags**, not proof of which source is correct.

## Appendix D. Coding-agent completion checklist

Each phase report: target commit; touched paths; source/derivative hashes; rights and human approvals (or missing); published vs staged vs blocked layers; browser and Python commands/results; staging files/hash audit; accessibility results; independent georeferencing control/checkpoint separation; unresolved risks. Avoid claims that live CDN rendering, release CI dependencies or hazard classifications are tested until they actually are.
