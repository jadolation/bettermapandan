# Better Mapandan GIS Implementation Plan

**Version:** 1.0  
**Prepared:** 18 October 2026  
**Status:** Planning / data inventory  
**Project:** Better Mapandan — independent civic information portal for Mapandan, Pangasinan

## 1. Executive summary

Build a GIS page within the existing Better Mapandan static website. The map should begin as a trustworthy geographic directory and then connect verified public facilities and infrastructure records to the site's existing transparency information. The first release should use Leaflet and static GeoJSON, be generated/deployed through the existing Python build and GitHub Pages workflow, and avoid adding a backend or PostgreSQL requirement.

**Primary rule:** locations, boundaries, and hazard areas are not authoritative merely because a coordinate or file is available. Keep source material, normalized GIS data, and website output separate. Every published layer must have provenance, currency, known limitations, and an explicit verification status.

### Desired outcome

A visitor can:
- view Mapandan and any reliably sourced barangay boundaries;
- toggle road/waterway, facility, project, and later hazard layers;
- inspect a facility or project and see its source and verification state;
- open a linked Better Mapandan project record where a defensible entity relationship exists; and
- understand when a location is approximate, unverified, out of scope, stale, or derived.

### Explicit non-goals for the first version

- No live emergency warning service or claim of real-time safety.
- No evacuation routing or "nearest safe shelter" recommendations.
- No claim that every school is an officially designated evacuation center.
- No fabricated barangay polygons from barangay-hall coordinates.
- No automatic linking of a public project to a map point based solely on a similar name or a barangay-level location.
- No new database/backend, live public API, or citizen incident-report workflow as part of this GIS MVP.
- No replacement of the existing Better Mapandan entity-resolution or provenance model.

## 2. Current website architecture constraints

Better Mapandan is an independent, static-site-generated, trilingual portal. Its Python build system reads canonical JSON and page templates, generates HTML for English, Filipino, and Pangasinan, and is tested/deployed through GitHub Actions. The existing site already uses Leaflet for an infrastructure map. Keep this architecture unless repository inspection reveals an intentional recent change.

Implementation implications:
1. Add a GIS page to the existing page/template and navigation/i18n systems rather than creating a separate application.
2. Store canonical and normalized map records as version-controlled data files. Keep unmodified source files separate from normalized outputs.
3. Use GeoJSON for data consumed by Leaflet where suitable.
4. Add GIS validation to existing CI; do not commit generated site output if the repository's existing workflow regenerates it.
5. Follow existing localization, CSP, asset-base, accessibility, and responsive-design conventions.
6. Inspect the current repository before selecting exact paths or replacing any map implementation. The paths suggested in this document are proposed, not confirmed existing files.

## 3. Data inventory available now

### 3.1 Administrative reference: PSA/PSGC list

The provided PSA table lists 15 barangays as of 31 July 2025. It supplies administrative identifiers, urban/rural classifications, and 2024 POPCEN values. These are attributes—not boundary geometries. Use codes as stable join keys and verify against the current PSA PSGC publication before release.

| Barangay | PSGC 10-digit code | Correspondence code | Urban/rural | Population (2024 POPCEN) |
|---|---:|---:|---|---:|
| Amanoaoac | 0105528001 | 015528001 | Rural | 1,656 |
| Apaya | 0105528002 | 015528002 | Rural | 1,650 |
| Aserda | 0105528003 | 015528003 | Rural | 1,414 |
| Baloling | 0105528004 | 015528004 | Rural | 4,238 |
| Coral | 0105528006 | 015528006 | Rural | 1,405 |
| Golden | 0105528007 | 015528007 | Rural | 1,432 |
| Jimenez | 0105528008 | 015528008 | Rural | 2,008 |
| Lambayan | 0105528009 | 015528009 | Rural | 1,682 |
| Luyan | 0105528010 | 015528010 | Rural | 3,344 |
| Nilombot | 0105528012 | 015528012 | Urban | 4,199 |
| Pias | 0105528013 | 015528013 | Urban | 4,827 |
| Poblacion | 0105528014 | 015528014 | Urban | 3,509 |
| Primicias | 0105528015 | 015528015 | Rural | 2,218 |
| Santa Maria | 0105528016 | 015528016 | Rural | 1,585 |
| Torres | 0105528018 | 015528018 | Rural | 3,061 |
| **Total** |  |  |  | **38,228** |

The row totals add up to 38,228, matching the municipality total shown in the supplied PSA listing. Keep the population year and source as metadata; do not treat population as a live count.

**Expected first data artifact:** a barangay reference JSON/CSV using `psgc_code` as a join key. It may drive a list/filter before boundary polygons are available.

### 3.2 Candidate barangay-hall / barangay-location points

The following coordinates were supplied as approximate barangay-hall or municipal-complex locations. They are candidate points, not barangay centroids and not administrative boundaries.

| Barangay / location | Latitude | Longitude | Current interpretation |
|---|---:|---:|---|
| Amanoaoac | 16.0223 | 120.4496 | Candidate barangay-hall point |
| Apaya | 16.0242 | 120.4459 | Candidate barangay-hall point |
| Aserda | 16.0264 | 120.4563 | Candidate barangay-hall point |
| Baloling | 15.9985 | 120.4531 | Candidate barangay-hall point |
| Coral | 16.0343 | 120.4510 | Candidate barangay-hall point |
| Golden | 16.0223 | 120.4419 | Candidate barangay-hall point |
| Jimenez | 16.0175 | 120.4618 | Candidate barangay-hall point |
| Lambayan | 16.0005 | 120.4699 | Candidate barangay-hall point |
| Luyan | 16.0292 | 120.4582 | Candidate barangay-hall point |
| Nilombot | 16.0238 | 120.4725 | Candidate barangay-hall point |
| Pias | 16.0221 | 120.4491 | Candidate barangay-hall point |
| Poblacion / Municipal Hall Complex | 16.0290 | 120.4530 | Candidate municipal/barangay point; confirm official name and role |
| Primicias | 16.0210 | 120.4398 | Candidate barangay-hall point |
| Santa Maria | 16.0298 | 120.4608 | Candidate barangay-hall point |
| Torres | 16.0151 | 120.4661 | Candidate barangay-hall point |

The source text also provides Plus Codes. Preserve them as source attributes if helpful, but do not rely on them instead of the decimal coordinates or treat either one as proof of exact site identity. Several school coordinates in the supplied list exactly reuse these candidate hall coordinates; these must be checked before the school points are published.

### 3.3 Candidate public safety, health, and school points

**Coordinate-source update (19 October 2026):** the additional Plus Codes in §3.5 below provide a newer coordinate candidate for the named locations. Where a facility appears in both this section and §3.5, keep the older decimal point as a conflicting source value in the review history; do not silently overwrite it or assume either value is correct until identity and location have been reconciled.

Coordinates below are transcribed from the supplied notes. They are **unverified candidates** until independently checked against the original source, an official directory, a map, or the responsible institution. Their inclusion here is an inventory, not a claim that they are correct or currently operating.

#### Police, fire, health, and other facilities

| Candidate facility | Latitude | Longitude | Initial QA note |
|---|---:|---:|---|
| Mapandan Municipal Police Station | 16.0289 | 120.4532 | Same coordinates as supplied for fire station; confirm whether truly colocated |
| Mapandan Fire Station | 16.0289 | 120.4532 | Same coordinates as supplied for police station; confirm before treating as two distinct sites |
| Mapandan Rural Health Unit (RHU) | 16.0285 | 120.4531 | Candidate health-facility point |
| Mapandan Community Hospital | 16.0281 | 120.4526 | Candidate point; verify address, coordinates, and Plus Code consistency |
| BUCAS Center | 16.0195 | 120.4485 | **Hold from public map**: source description says “Tubao, La Union” while also describing it as a Mapandan/Torres facility; municipality/location conflict must be resolved |
| Tulagan Multi-Purpose Gymnasium | 16.0286 | 120.4521 | Reported gym / possible relief-use facility; not automatically an official evacuation center |
| Mapandan Town Center | 16.0248 | 120.4535 | Source labels it as a shopping mall and describes an assembly role; confirm the actual place identity and any official emergency designation |

#### Secondary/high schools supplied

| Candidate school | Latitude | Longitude | Initial QA note |
|---|---:|---:|---|
| Mapandan National High School / Central School SPED Center | 16.0245 | 120.4542 | Name combines institutions; separate identities and source coordinates need checking |
| Baloling National High School | 15.9982 | 120.4528 | Verify school level and exact point |
| Torres National High School | 16.0198 | 120.4491 | Description says Salomague / Torres boundary; verify location and barangay association |
| Primicias National High School | 16.0210 | 120.4398 | Coordinates are reused for Primicias hall and elementary school; verify before mapping as an independent facility |

#### Elementary schools supplied

| Candidate school | Latitude | Longitude | Initial QA note |
|---|---:|---:|---|
| Mapandan Central School SPED Center | 16.0279 | 120.4534 | Differs from the combined high-school/SPED entry above; verify if these are separate sites or conflicting records |
| Jimenez Elementary School | 16.0098 | 120.4650 | Candidate school point |
| Nilombot Elementary School | 16.0281 | 120.4364 | **High-priority QA**: coordinate is far from the supplied Nilombot hall point at 120.4725 longitude; verify against official address/source |
| Baloling Elementary School | 15.9985 | 120.4528 | Exactly reuses candidate Baloling hall point; likely needs a school-specific coordinate check |
| Lambayan Elementary School | 16.0005 | 120.4699 | Exactly reuses candidate Lambayan hall point; verify |
| Torres Elementary School | 16.0150 | 120.4689 | Candidate school point; verify |
| Luyan Elementary School | 16.0292 | 120.4582 | Exactly reuses candidate Luyan hall point; verify |
| Pias Elementary School | 16.0221 | 120.4491 | Exactly reuses candidate Pias hall point; verify |
| Primicias Elementary School | 16.0210 | 120.4398 | Exactly reuses candidate Primicias hall point; verify |
| Santa Maria Elementary School | 16.0298 | 120.4608 | Source says “Closed”; verify current operational status and source date before displaying it as open/active |
| Amanoaoac Elementary School | 16.0223 | 120.4496 | Exactly reuses candidate Amanoaoac hall point; verify |
| Golden Elementary School | 16.0223 | 120.4419 | Exactly reuses candidate Golden hall point; verify; source says “Closed,” which requires current confirmation |

Do not infer that two entries are duplicates just because their coordinates are equal, and do not infer they are different facilities just because their names differ. Add explicit QA states and resolve the identity from better sources.

### 3.4 Hazard data already held

| Asset | Known from current notes | Next required action |
|---|---|---|
| KMZ file 1 | Ground-shaking data | Preserve original; inspect KML layer structure, geometry, metadata, legend, source agency, date, and coordinate reference system; preview in QGIS/Google Earth |
| KMZ file 2 | Liquefaction data | Same review; determine whether it contains polygons, paths, placemarks, or a GroundOverlay image |
| Mapandan government hazard map | Official municipal website has a “Mapandan Hazard Map” page published 2 September 2020 | Download/preserve original image or document; record URL/date/agency; inspect its legend and geographic reference. Do not assume an image is GIS geometry |
| Health-centre coordinates | User reports these are available; several are in the notes above | Identify exact source file and source date, then reconcile facility names and points |
| School/police/fire coordinates | Candidate points listed above | Verify each facility's identity, coordinates, status, and source |
| Barangay PSGC table | 15 barangays, codes, urban/rural classes, 2024 population | Preserve as official reference attributes; obtain boundaries separately |

For the hazard layers, do not infer that an unavailable or unparsed KMZ layer means there is no hazard. Do not publish a hazard-colored region until its meaning, coverage, legend, source, and data date are understood.

### 3.5 New facility location references supplied as Google Maps Plus Codes (19 October 2026)

The following short Plus Codes were supplied with locality context by the project maintainer. They have been expanded using the official Open Location Code `recoverNearest` algorithm relative to an approximate Mapandan reference point of **16.030000, 120.455000**. The resulting decimal coordinates are the **centres of the decoded Plus Code cells**, not surveyed coordinates and not proof that the named institution is correctly identified or currently operating.

For reproducibility, the recovered full Plus Code is recorded beside the original short code. The full-code prefix is inferred from the Mapandan reference locality; confirm the result by opening the full code in Google Maps or checking it with the responsible institution before publication. The OLC specification explicitly says shortened codes require a nearby reference location and decoding returns an area, not an exact surveyed point. See: https://github.com/google/open-location-code/blob/main/README.md and https://github.com/google/open-location-code/blob/main/Documentation/Specification/specification.md.

- Datum/coordinate convention: WGS84 geographic coordinates; list latitude first, longitude second.
- Codes with three characters after `+` produce an approximately 2.8 m × 3.3 m cell at Mapandan latitude; codes with two characters after `+` produce an approximately 14 m × 13 m cell. Decimal places in the displayed cell-centre coordinate do not increase the actual accuracy of the source.
- Preserve the user's original short code, the recovered full code, the reference point used, retrieval/conversion date, and method (e.g. `open_location_code_recover_nearest`).
- These results are candidate points for review, not automatic approval to publish. Where they conflict with older points, a mapped footprint, a locality/address, or facility identity, retain both candidates and resolve the contradiction.
- This table supersedes earlier candidate decimal values only as a *new candidate source*, not as verified ground truth.

#### Evacuation-centre candidates and associated facilities

| Place / facility | Original short Plus Code | Recovered full Plus Code | Latitude (cell centre) | Longitude (cell centre) | Precision / review note |
|---|---|---|---:|---:|---|
| Mapandan Central School | `2FG3+XFW` | `7Q822FG3+XFW` | 16.0274875 | 120.4537031 | ~2.8 m × 3.3 m code cell; confirm school identity and designated evacuation role |
| Aloha Building, Firetree Ave | `2FG3+HMQ` | `7Q822FG3+HMQ` | 16.0264625 | 120.4542344 | Code-derived point; no previous coordinate available |
| Tulagan Gym / Cong. Tulagan Gym | `2FG3+FJX` | `7Q822FG3+FJX` | 16.0262375 | 120.4541094 | Conflicts with earlier candidate (16.028600, 120.452100); review both |
| Coral Barangay Hall | `2FJ2+CQH` | `7Q822FJ2+CQH` | 16.0310625 | 120.4519844 | Conflicts with earlier supplied point (16.034300, 120.451000); review both |
| Primicias Elementary School | `XFWH+CRF` | `7Q72XFWH+CRF` | 15.9960625 | 120.4795469 | Conflicts materially with older supplied point (16.021000, 120.439800); mapped OSM campus centroid is similar but identity/location still needs source reconciliation |
| Primicias National High School | `XFWH+9X2` | `7Q72XFWH+9X2` | 15.9958875 | 120.4798906 | Conflicts materially with older supplied point (16.021000, 120.439800); check against school source |
| Santa Maria Elementary School | `2FH9+H73` | `7Q822FH9+H73` | 16.0288875 | 120.4681719 | Conflicts with older supplied point (16.029800, 120.460800); confirm current operating status |
| Baloling Elementary School | `2FP4+VVR` | `7Q822FP4+VVR` | 16.0372375 | 120.4571406 | Conflicts materially with older supplied point (15.998500, 120.452800); mapped OSM school footprint lies nearby but needs reconciliation |
| Jimenez Elementary School | `2F58+V27` | `7Q822F58+V27` | 16.0096625 | 120.4650469 | Close to older candidate (16.009800, 120.465000); still source-verify |
| Lambayan Elementary School | `2F2C+35P` | `7Q822F2C+35P` | 16.0002125 | 120.4704531 | Close to older candidate (16.000500, 120.469900); still source-verify |
| Nilombot Elementary School | `2CHP+7H2` | `7Q822CHP+7H2` | 16.0281375 | 120.4363906 | Consistent with older candidate (16.028100, 120.436400); resolve separate hall point conflict |
| Golden Elementary School | `2CFR+4RV` | `7Q822CFR+4RV` | 16.0228625 | 120.4420469 | Near older candidate (16.022300, 120.441900); confirm operating status |
| Torres Elementary School | `2F89+4JH` | `7Q822F89+4JH` | 16.0153125 | 120.4691094 | Near older candidate (16.015000, 120.468900); reconcile locality/official school record |

#### Health facilities

| Place / facility | Original short Plus Code | Recovered full Plus Code | Latitude (cell centre) | Longitude (cell centre) | Precision / review note |
|---|---|---|---:|---:|---|
| Mapandan Rural Health Unit (RHU) | `2FG3+9P` | `7Q822FG3+9P` | 16.0259375 | 120.4543125 | ~14 m × 13 m code cell; conflicts with older candidate (16.028500, 120.453100) |
| Mapandan Community Hospital | `2FF4+RH` | `7Q822FF4+RH` | 16.0245625 | 120.4564375 | ~14 m × 13 m code cell; aligns closely with mapped hospital footprint but conflicts with older candidate (16.028100, 120.452600) |
| BUCAS Center | `2F5F+C4` | `7Q822F5F+C4` | 16.0085625 | 120.4728125 | ~14 m × 13 m code cell; old record says Tubao, La Union and gave different coordinates (16.019500, 120.448500); identity/locality conflict remains blocking |

#### Emergency responders and government facility

| Place / facility | Original short Plus Code | Recovered full Plus Code | Latitude (cell centre) | Longitude (cell centre) | Precision / review note |
|---|---|---|---:|---:|---|
| Mapandan Municipal Police Station | `2FG3+R7W` | `7Q822FG3+R7W` | 16.0271125 | 120.4532031 | ~2.8 m × 3.3 m code cell; same code as fire station, confirm independent identities/sites |
| Mapandan Fire Station | `2FG3+R7W` | `7Q822FG3+R7W` | 16.0271125 | 120.4532031 | Same source cell as police station; blocked as a separately verified point until reviewed |
| Municipal Hall | `2FG3+Q5` | `7Q822FG3+Q5` | 16.0269375 | 120.4529375 | ~14 m × 13 m code cell; conflicts with older municipal-complex candidate (16.029000, 120.453000); confirm exact facility and address |

**Important correction for the existing facility inventory:** the user-supplied Plus Codes are new source evidence, but they do not by themselves resolve every contradiction. In particular, BUCAS still conflicts with the older locality/address record; police and fire still use the same code; and several older decimal coordinates materially disagree with the converted cells. The public GIS must not publish those as verified merely because the recovered values look precise.

## 4. Data acquisition strategy

Use sources in this order, subject to availability, terms, and data quality:

1. **PSA/PSGC** — official barangay names/codes, administrative status, and population metadata. Use the latest relevant PSGC version for the production dataset; retain the supplied 31 July 2025 reference as historical source context where applicable.
2. **Municipality of Mapandan** — hazard map, evacuation-centre information, official facility lists, and corrections from responsible offices.
3. **Geoportal Philippines / appropriate government geospatial agency** — candidate administrative boundaries and hazard layers; inspect each layer's metadata and download/use conditions.
4. **OpenStreetMap via Overpass Turbo** — supplementary roads, waterways, buildings, and mapped amenities. Coverage is incomplete and tags can vary. OSM features must not silently override official records.
5. **DepEd/DOH or other relevant agency directories** — candidate institution records that can be reconciled to geographic points.
6. **Field/office verification** — record who checked an uncertain point, when, and how. Avoid collecting unnecessary personal information.

### Overpass Turbo troubleshooting and extraction

Do not rely on `{{geocodeArea:...}}` being able to resolve Mapandan. Previous tests returned no visible Mapandan results. Use this approximate bounding-box fallback for discovery, not as an official municipal boundary:

```overpass
[out:json][timeout:60];
(
  nwr["highway"](15.98,120.42,16.05,120.49);
  nwr["waterway"](15.98,120.42,16.05,120.49);
);
out geom;
```

Overpass bounding-box order is south, west, north, east. After running the query, inspect both the Data tab and map; use “Zoom to data” if records exist but the map remains centered on its default viewport. Zero results indicate there may be no matching tagged objects in the selected box, not that the real-world features do not exist. Export separate GeoJSON files per theme. Do not combine all data types into one hard-to-audit file.

OpenStreetMap data is licensed under ODbL and requires attribution and compliance with its terms. If published map data or derived databases use OSM data, assess the share-alike implications before release. Always retain a clear attribution such as “© OpenStreetMap contributors” with a link to https://www.openstreetmap.org/copyright.

## 5. Recommended GIS data model

Keep **raw files**, **normalized data**, and **published output** distinct. Suggested paths are provisional; inspect the current repository before deciding exact paths.

```text
datasets/gis/
  raw/
    kmz/
    municipal-hazard-map/
    osm/
    official-directories/
  manifests/
  review/

src/data/gis/
  barangays.json
  facilities.geojson
  roads.geojson
  waterways.geojson
  hazard-layers.json
  projects.geojson
  layers.json

assets/js/
  gis-map.js
```

Keep any original input bytes immutable under an agreed raw-data workflow. The canonical layer files should be generated or manually reviewed from raw sources; never hand-edit a derived file without documenting the process.

### Common feature properties

Each feature should include fields where applicable:

- `id`: stable internal ID; do not use a display name as the only identifier.
- `name`, `name_fil`, `name_pag`: where relevant and human-reviewed.
- `feature_type` or a controlled category.
- `psgc_code`: for a barangay association when established.
- `source_name`, `source_url`, `source_record_id`.
- `source_as_of`, `retrieved_at`, `last_verified_at`.
- `verification_status`: e.g. `unreviewed`, `source_verified`, `field_verified`, `rejected`, `needs_review`.
- `location_precision`: e.g. `exact_from_source`, `approximate`, `barangay_level`, `unknown`.
- `geometry_source` and any conversion/processing notes.
- `linked_entity_ids`: only for verified or appropriately labelled Better Mapandan entity relationships.

Prefer separate provenance records for multiple sources rather than flattening them to one URL. Do not put sensitive reporter information into GIS layers.

### Administrative boundaries versus barangay reference points

- A PSGC row is an administrative identity and attribute record; it cannot draw a polygon.
- A barangay-hall point locates a hall, not an entire barangay.
- A centroid must be calculated from a validated polygon; do not use a hall point and call it a centroid.
- Never draw guessed polygons from the coordinates or Plus Codes in the source notes.
- If no valid barangay boundary geometry can be obtained, release the map with a barangay directory/filter and clearly identified reference points instead of fictional boundaries.

## 6. GIS page behavior

### MVP interaction

- Responsive Leaflet map that works on desktop and mobile.
- Appropriate base tiles with visible attribution.
- Layer control with independent toggles, initially: facilities, roads/waterways (only if data is ready), and future hazard/project layers hidden or disabled until reviewed.
- Category filters for school, health, police, fire, barangay hall, and other facility types.
- Search by a facility name or barangay name, if supported by the available data.
- Clickable feature details showing name, type, barangay association when verified, source link, source date, verification state, and limitations.
- Clear empty/loading/error states; failure to load one optional layer must not break the entire map.
- Links to existing Better Mapandan project records only when a reliable `linked_entity_ids` relationship exists.
- Keyboard-accessible controls and readable labels; map interactions must not be the only way to access important information.

### Hazard display rules

- Show each layer's legend, agency/source, data date, and intended interpretation.
- Distinguish hazard susceptibility/intensity data from live conditions and official warnings.
- Make no “safe/unsafe” or evacuation-routing conclusion without a validated methodology and authorized/current inputs.
- Keep hazard layers off by default until the file and legend have been inspected and correctly represented.
- If the supplied hazard map is only an image, do not stretch or overlay it as if accurately georeferenced. Georeference only with documented control points and a measured/recorded transformation quality.

### Projects overlay rules

Reuse existing Better Mapandan entity IDs and source trails. A project can be:
- point geometry if the source identifies a specific site;
- line geometry if it is a road, bridge, or other linear asset with supported geometry;
- polygon geometry if the official/acceptable source provides a site or boundary polygon;
- unlocated / barangay-level if only the barangay is known.

Do not assign precise project coordinates from a project title, contractor address, generic barangay name, or AI guess. Keep unmappable projects available in the normal Project Explorer.

## 7. Implementation phases and deliverables

### Phase 0 — Repository and data audit

Tasks:
1. Inspect the current repository, build flow, navigation/localization files, existing Leaflet implementation, CSP, asset paths, CI, and tests.
2. Locate both KMZ files and the government hazard-map file/URL; preserve their originals and identify their licenses/source metadata.
3. Create a data inventory and validation report for all candidate points and known inconsistencies.
4. Verify 15 barangay names and PSGC codes against the current PSA source.
5. Decide where GIS files should live based on existing conventions.

Deliverables: `gis-data-inventory.md` or equivalent; documented raw-source registry; no public map layer published yet.

### Phase 1 — GIS foundation and data contract

Tasks:
1. Define schemas for layer manifest, feature properties, source provenance, review state, and geometry type.
2. Add GIS data validation script(s) and tests: valid coordinate ranges, valid GeoJSON, unique feature IDs, allowed statuses, source metadata, expected 15 PSGC rows, population sum, and no silently blank layer on source failure.
3. Create the canonical barangay reference table from the PSA data, retaining population reference year and administrative code.
4. Set up a reproducible way to inspect/convert GeoJSON and KMZ (e.g. QGIS or GDAL/OGR if installed); conversion must be tested and documented.

Deliverables: schemas, validation checks, and trustworthy barangay reference data. Still no invented boundaries.

### Phase 2 — Minimal interactive map

Tasks:
1. Add the GIS page using site templates, locale strings, current navigation, and CSP conventions.
2. Use Leaflet, existing base-map conventions if suitable, responsive layout, attribution, and empty/error/loading states.
3. Start centered using the bounds of confirmed Mapandan features or a reasonable default view; do not leave the map at Overpass Turbo's Rome viewport.
4. Show candidate point data only with a visible “unverified / approximate” status if the project owner wants to show a review preview. Production public layers should default to reviewed records only.
5. Provide an accessible list/search alternative for mapped facilities.

Deliverables: a functioning map page using the smallest reviewed dataset, plus build tests.

### Phase 3 — Municipal and barangay boundaries, roads, waterways

Tasks:
1. Search official/geospatial sources for the municipality boundary and all 15 barangay polygons.
2. If using OSM, query a bounded area and inspect the returned Data tab; do not depend exclusively on `geocodeArea`.
3. Check polygon validity, CRS, name/code matches, overlaps, gaps, and coverage; document known limitations.
4. Add roads and waterways as separate layers after geometry/source/license checks and performance checks.
5. If reliable polygons are unavailable, ship the reference table and candidate hall points only; do not fabricate polygons.

Deliverables: validated boundary/linear layers where available, or a documented data gap and safe fallback.

### Phase 4 — Facility reconciliation

Tasks:
1. Standardize types and names from the supplied school/health/safety lists.
2. Resolve suspicious coordinates, duplicated/reused points, status conflicts, location-text conflicts, and non-Mapandan entries.
3. Compare against OSM and relevant official directories; preserve per-source evidence.
4. Publish only reviewed entries by default; provide correction workflow to improve the inventory.

Priority review queue:
- Reconcile the newer Plus Code-derived point and older decimal candidate for every facility in §3.5; materially conflicting pairs remain blocked.
- BUCAS: old source says Tubao, La Union and gave 16.019500, 120.448500; new short code supplied with Mapandan context resolves to 16.0085625, 120.4728125. Preserve both candidates and resolve the facility identity/locality.
- Police and fire station: both new entries use 2FG3+R7W and resolve to 16.0271125, 120.4532031; confirm whether the facilities are colocated or one record uses a reused code.
- Tulagan Gym, Coral Barangay Hall, Mapandan RHU, Community Hospital, Municipal Hall, Primicias schools, Santa Maria Elementary, and Baloling Elementary have material differences between older decimal points and new code-derived centers; investigate using the responsible institution / source map.
- Combined Mapandan National High School / Central School SPED Center versus separately mapped schools: resolve identity and keep separate source IDs where distinct.
- Nilombot Elementary's Plus Code coordinate (16.0281375, 120.4363906) agrees with its older school coordinate, while Nilombot Barangay Hall is at a different candidate point; verify each independently rather than treating this as a contradiction by proximity alone.
- Multiple elementary school points exactly matched barangay-hall points in the older list; the new school Plus Codes provide separate candidates for several schools. Preserve the historical candidates and resolve them rather than overwriting silently.
- Santa Maria and Golden school records are labelled “Closed” in the supplied notes: verify current status; never infer current closure from undated content.
- Mapandan Town Center's stated evacuation/assembly role and Tulagan gym's shelter role: confirm formal designation with appropriate local source before using the official “evacuation center” category.

Deliverables: reviewed facility GeoJSON and a rejected/needs-review list kept outside the public map.

### Phase 5 — Hazard layers

Tasks:
1. Inspect KMZ files and the municipal hazard map; record metadata, source, date, legend, geography, projection, and intended meaning.
2. Convert vector geometries where valid; if a KMZ contains an image overlay, assess georeferencing separately.
3. Verify ground shaking and liquefaction layers describe the intended hazard category, units/classification, and coverage.
4. Add legends and interpretive notes; visually compare with the source in GIS software.
5. Keep layers disabled or unpublished while critical metadata or transformations remain unresolved.

Deliverables: independently validated hazard GeoJSON/tiles if supported, source notes, and a clear “not real-time warning” caveat.

### Phase 6 — Better Mapandan project connections

Tasks:
1. Inspect the current project entity data and stable IDs.
2. Add location references only when supported by source evidence; store the relation to existing entity IDs.
3. Use exact project point/line/polygon geometry only when supported; otherwise use an explicit unlocated/barangay-level status.
4. Link map popups into the existing Project Explorer and expose source trail/match confidence.
5. Add tests that project matching never auto-promotes uncertain spatial proximity/name matches to confirmed relationships.

Deliverables: map-to-project integration with no parallel invented project registry.

### Phase 7 — Polish, accessibility, CI, and release

Tasks:
1. Test mobile/responsive behavior, keyboard controls, popup focus, layer toggles, low-bandwidth use, and layer load failures.
2. Add automated GIS checks to existing CI and verify the full trilingual build.
3. Verify OpenStreetMap attribution/ODbL notice and terms of any alternate tile provider.
4. Validate displayed counts against data; add per-layer updated dates and coverage/quality notes.
5. Run a final evidence review with local knowledge holders before featuring disaster-related information prominently.

Deliverables: production-ready GIS page and documented update workflow.

## 8. Acceptance criteria

The MVP is ready for public review when:

- [ ] The GIS page is integrated into the existing site and generated for all supported locales using existing conventions.
- [ ] The map focuses on Mapandan/available records rather than defaulting to Rome or another unrelated view.
- [ ] OSM/other base-map attribution is visible and licensing conditions are documented.
- [ ] No invented barangay polygons or guessed project sites are published.
- [ ] Every displayed facility has a stable ID, source/provenance, and visible/accessible verification state.
- [ ] All known coordinate contradictions above are resolved or excluded from public display.
- [ ] Every supplied short Plus Code is preserved alongside its recovered full code, reference location, conversion method, and cell-centre coordinates; decimal digits are not represented as survey accuracy.
- [ ] Material differences between older decimal points and Plus Code-derived candidate points are reconciled or excluded from publication.
- [ ] Official names and PSGC codes are validated against the relevant PSA reference.
- [ ] Hazard layers have source, date, legend, coverage, and correct interpretation; unresolved layers are not published.
- [ ] Data validation rejects malformed GeoJSON, invalid coordinates, duplicate IDs, and absent provenance where required.
- [ ] One failed/missing layer does not make the whole map unusable.
- [ ] Keyboard-accessible controls and a non-map way to browse essential facility records are available.
- [ ] Existing site tests, data checks, localization checks, and deployment build pass.
- [ ] Documentation explains updating sources, rebuilding, reviewing changes, licenses, and known data gaps.

## 9. Suggested success measures

Track these during development:
- Number of the 15 barangay polygons sourced and validated (do not inflate this count using hall points).
- Number of facility records that have been source-checked and coordinate-checked.
- Number of features with complete provenance and date/status metadata.
- Number of unresolved records excluded from public layers.
- Number of known invalid geometries/coordinates caught by tests.
- GIS page performance and usability on mobile devices.
- Number of links from verified map features to existing Better Mapandan project entities.

## 10. Immediate next actions

1. Locate and inventory the two KMZ files and the original municipal hazard-map asset.
2. Create/update the coordinate inventory with all new short Plus Codes from §3.5 expanded using the official Open Location Code recovery algorithm relative to the recorded Mapandan reference point; preserve original codes, recovered full codes, cell centres, and conflicting older candidates as *unreviewed*.
3. Download/export a small Overpass sample using the approximate bounds `15.98,120.42,16.05,120.49` (south, west, north, east). If the map remains elsewhere, inspect Overpass Turbo's **Data** tab and use **Zoom to data**; zero results are not proof that features do not exist.
4. Find an appropriate boundary polygon source for Mapandan and the 15 barangays. Do not attempt to derive polygons from the 15 point coordinates.
5. Inspect the current repository before code changes and then implement Phase 1 before adding the public map layer.

## References and source starting points

- PSA, Mapandan barangays and PSGC attributes: https://psa.gov.ph/classification/psgc/barangays/0105528000
- Municipality of Mapandan, Disaster Awareness: https://mapandan.gov.ph/disaster-awareness/
- Municipality of Mapandan, Mapandan Hazard Map (published 2 September 2020): https://mapandan.gov.ph/disaster-awareness/mapandan-hazard-map/
- Geoportal Philippines: https://www.geoportal.gov.ph/
- Overpass Turbo documentation: https://dev.overpass-api.de/overpass-doc/en/targets/turbo.html
- OpenStreetMap copyright and license: https://www.openstreetmap.org/copyright
- Leaflet documentation: https://leafletjs.com/reference
- DepEd school masterlist: https://ebeis.deped.gov.ph/beis/reports_info/masterlist
- DOH National Health Facility Registry: https://nhfr.doh.gov.ph/VActivefacilitiesList

The exact availability, currency, license, and download terms of each external dataset must be checked during implementation; a listed portal is a starting point, not a guarantee that a required file or API is available.
