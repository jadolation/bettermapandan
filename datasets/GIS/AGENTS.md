# AGENTS.md — Better Mapandan GIS Implementation

This file instructs coding agents working on the GIS map task in the existing Better Mapandan repository. Treat it as project-specific implementation guidance, not permission to invent, publish, or silently verify geographic information.

## 1. Mission

Build an interactive GIS page for Mapandan, Pangasinan, using reviewed geographic data and the existing Better Mapandan static-site architecture. The GIS should progressively combine:

1. Barangay reference data and verified boundaries, if obtainable.
2. Roads and waterways.
3. Public facility points (schools, health facilities, police/fire stations, barangay halls, and verified evacuation centres).
4. The existing Better Mapandan infrastructure/project records, but only where geographic relationships are supported.
5. Ground-shaking and liquefaction KMZ layers and the municipality's hazard map, only after the original data, projection, metadata, legend, and limitations are understood.

Read `bettermapandan-gis-implementation-plan.md` before implementation if it is present in the working context/repository. If the plan is not in the repository, request it or use the provided project task brief rather than inventing missing data.

## 2. Inspect before changing code

Before editing, inspect the repository structure and determine:

- The actual static-site generator entry point and build commands.
- How source pages are declared, localized, and added to navigation.
- Existing Leaflet/map scripts, CSS conventions, CSP, attribution, and asset-base handling.
- Where the existing DPWH/project datasets and entity IDs live.
- Existing schemas, tests, CI workflows, and generated-output rules.
- Whether there are already GIS data directories or map-specific components.

Do not assume example paths from the plan already exist. Prefer extending existing modules and conventions over making a parallel framework. Do not add a frontend build system, runtime server, database, or framework unless there is a documented, approved requirement.

## 3. Architecture constraints

- Preserve the existing static-site generation and GitHub Pages deployment model.
- Use Leaflet and GeoJSON when appropriate and consistent with the current site.
- Store original/raw source files separately from normalized/canonical GIS data and generated site output.
- Do not commit generated files if the existing build process generates and ignores them.
- Follow current English, Filipino, and Pangasinan localization patterns.
- Reuse existing Better Mapandan entity IDs and provenance contracts; do not create a second incompatible project entity system.
- Make the GIS page optional-data tolerant: if one layer fails, other layers and the overall page must still work.
- Do not introduce a public API, PostgreSQL, a citizen incident-reporting backend, or live emergency-routing claims as part of the GIS MVP.

## 4. Data trust and non-negotiable rules

### 4.1 Never invent spatial data

- The PSA/PSGC list provides names/codes and population attributes. It does **not** provide boundary geometry.
- A barangay-hall point is not a barangay polygon, centroid, or representative boundary.
- Never create approximate barangay polygons from point coordinates or Plus Codes.
- Do not assign project coordinates based on a title, nearby facility, contractor address, or AI guess.
- If boundaries cannot be sourced and validated, provide the barangay list/filter and verified point features instead; document the gap.

### 4.2 Treat supplied coordinates as unverified candidates

The submitted coordinates can contain copy errors, outdated locations, mismatched names, closed sites, or approximate rather than exact points. Do not publish them as verified solely because they were supplied in a chat or copied from a listing.

High-priority issues from the current inventory:

- BUCAS is described as “Tubao, La Union” while also described as a Mapandan/Torres facility. Keep it out of the public Mapandan layer until identity/location is resolved.
- Police and fire station points share exactly the same coordinates. Check whether they are colocated or a copied value.
- The combined “Mapandan National High School / Central School SPED Center” and separate “Mapandan Central School SPED Center” have different points and potentially conflated names.
- Nilombot Elementary's longitude (`120.4364`) conflicts with the supplied Nilombot hall longitude (`120.4725`); independently verify.
- Several elementary-school coordinates exactly reuse barangay-hall coordinates. Treat them as probable placeholders/copied coordinates until checked.
- Primicias school/hall entries share a coordinate; verify distinct sites.
- Santa Maria and Golden school records were marked “Closed” in the supplied notes. Verify current status rather than assuming current closure.
- Mapandan Town Center and Tulagan Gym have descriptions related to assembly/shelter use, but do not label them official evacuation centres without authoritative confirmation.
- Any facility whose Plus Code, address, municipality, and coordinates disagree must be marked `needs_review` and excluded from public map layers until resolved.

Do not collapse two records just because they share coordinates, and do not treat identical coordinates as proof that two locations are distinct.

### 4.3 Preserve provenance and status
- **Publication status is separate from source status.** `source_verified` means a source record was checked/transcribed; it does not establish identity, coordinate accuracy, current operational status, evacuation designation, or approval to publish.
- Do not change a verification status merely to make the map show markers or satisfy a test. Status changes require cited evidence and a documented review decision.
- Until the data schema has separate identity/location/publication fields, any known blocking contradiction must set the affected feature's existing `verification_status` to `needs_review` and exclude it from public output.

Every canonical feature should carry, where available:

- Stable internal `id`.
- Name and controlled feature category.
- Source name, source URL, source record ID, and source as-of/publication date.
- Retrieval time and last verification time.
- Verification state (`unreviewed`, `source_verified`, `field_verified`, `needs_review`, `rejected`, or an established project equivalent).
- Location precision (`exact_from_source`, `approximate`, `barangay_level`, `unknown`, or an established equivalent).
- Geometry source and transformation notes where applicable.
- Existing Better Mapandan entity IDs only when the relationship is supported.

Keep source-reported facts distinct from Better Mapandan calculations and AI proposals. Preserve all significant limitations. Use `null` or a review state for missing information; do not fill gaps with guesses.

### 4.4 Numerical coordinates are not automatically exact

When a user requests numerical coordinates, provide decimal latitude and longitude where a candidate coordinate exists, but do not describe decimal formatting as proof of positional accuracy.

- Coordinates copied from Plus Codes, search snippets, user-supplied lists, or general map listings are candidate values until their facility identity and location are corroborated.
- Coordinates computed from the centroid of an OSM school/building polygon are derived representative points, not the source's surveyed entrance coordinates. Record `coordinate_method: polygon_centroid`, source feature ID, retrieval date, and `location_precision: approximate` (or equivalent). Do not use "exact" or "field-verified" for these.
- When sources disagree materially, preserve the separate candidate coordinates in the review record. Do not silently average, overwrite, or select the coordinate that best fits the expected area.
- If no reliable numerical point can be found, leave the coordinate missing and record the retrieval/review gap. Do not invent a point from the barangay name, hall, another facility, or approximate administrative bounds.
- A coordinate may be published only if the publication gate in this document passes. A known contradiction blocks the feature even if another source has a numerically precise-looking coordinate.
- Public UI wording must distinguish source-reported coordinates, approximate points, footprint-derived centroids, and field-verified positions. Number of decimal places must not be interpreted as measurement accuracy.

### 4.4 Mandatory publication gate (corrective rule)

The publication gate is authoritative if any older comments, data notes, tests, manifest entries, or UI labels disagree with it.

A facility is publishable only when all of the following are true:

1. The source and facility identity are sufficiently established for the displayed claim.
2. The coordinates are supported by evidence appropriate to the stated `location_precision`.
3. No unresolved blocking review issue references the feature ID.
4. The feature is in an approved publication state under the current schema and has required provenance.
5. The public wording accurately states whether the coordinates are source-reported, approximate, derived from a mapped footprint, or field-verified.

Specific application to the current facility inventory:

- `fac-005` (BUCAS) is blocked until the Tubao, La Union vs. Mapandan location/identity contradiction is resolved.
- `fac-001` and `fac-002` are blocked as individually located public facilities until the shared police/fire coordinates are explained or independently verified. Identical coordinates do not prove that two sites are the same or different.
- `fac-006` is blocked until the possibly conflated school identity is resolved.
- Any facility covered by an unresolved issue stating its location fields conflict, its coordinates may be copied, or its locality is uncertain must remain blocked until a review decision cites resolving evidence.
- A record may be listed as source-verified while its location is not verified; source status alone must never open the publication gate.

Enforce this gate during the Python build, before candidate records are injected into public HTML or copied into public GIS assets. The browser-side filter is defense in depth, not the publication boundary: excluded facilities must not remain embedded in the public page payload. Internal review notes should not be copied to public artifacts unless they are deliberately rewritten as suitable public-facing uncertainty notes.

The manifest must not claim an implemented/available layer unless the relevant file is emitted to the build output and the runtime has a handler for its declared type. A metadata entry or a passing schema test alone is not evidence that a layer is rendered.

## 5. GIS tooling and data-source practices

- Use Overpass Turbo/OpenStreetMap as a supplementary source for roads, waterways, buildings, and mapped amenities, not as an assumed complete or authoritative facility inventory.
- If `{{geocodeArea:...}}` does not resolve Mapandan, use a bounded query with the supplied approximate discovery bounds: south `15.98`, west `120.42`, north `16.05`, east `120.49`. Clearly label these as approximate extraction bounds, not an official boundary.
- Overpass bounding-box order is south, west, north, east.
- If a query appears blank, inspect both the Data tab and the map viewport; use “Zoom to data” when results exist but the viewport has not moved. Zero results do not prove the feature is absent in the real world.
- Export theme-specific files. Do not combine roads, buildings, schools, and hazards into one unreviewable giant file.
- Keep source asset bytes and source URLs/dates. Verify the availability, license, and intended usage of each layer before redistribution.
- OpenStreetMap attribution must be displayed in a suitable place and link to https://www.openstreetmap.org/copyright. Assess ODbL obligations when publishing OSM data or a derived database.
- Inspect each KMZ before conversion. Determine if it contains vector geometry, placemarks, or image GroundOverlays. Confirm CRS, coverage, legend, source, date, and semantics. A KMZ extension alone does not establish a GIS layer's meaning or accuracy.
- Do not publish the municipality's 2020 hazard-map image as an accurately georeferenced GIS overlay unless it is georeferenced using documented controls and its transformation error/limitations are recorded.

## 6. Implementation sequence

Work in small, testable changes, in this order:

1. **Repository and data audit:** inspect architecture, locate raw GIS assets, inventory coordinates, validate current PSGC reference, and record issues. Do not build UI around unverified assumptions.
2. **Schemas and validation:** define/extend schemas and checks for GeoJSON validity, valid coordinates, unique IDs, required provenance, known status values, PSGC row count/codes, and dataset metadata.
3. **Minimal map page:** add page/navigation/localization following site patterns, use Leaflet and proper attribution, add loading/empty/error UI, focus the view on Mapandan/available data, and support accessible facility list/search where feasible.
4. **Boundaries and line data:** obtain/inspect authoritative or properly licensed municipal/barangay boundaries, roads, and waterways. If boundaries cannot be validated, do not draw them.
5. **Facility reconciliation:** validate supplied school, health, police/fire, and hall points against official directories, geographic sources, or local confirmation. Public map defaults to reviewed records.
6. **Hazard layers:** inspect and validate both KMZs and the municipal map before display. Add appropriate legends and a non-real-time disclaimer.
7. **Project overlays:** add only defensible point/line/polygon geometry and link to existing project entities via stable IDs. Unlocated or barangay-level projects remain available in Project Explorer without fake point precision.
8. **CI, accessibility, and release:** test mobile behavior, keyboard access, missing-layer handling, source attribution, locale build, and existing quality gates.

## 7. Code and UI quality requirements

- Keep styles consistent with Better Mapandan design tokens and responsive conventions.
- Use separate, understandable layer modules or data loaders rather than a single monolithic script, consistent with existing repository conventions.
- Create a layer manifest defining layer ID, title/localized labels, data URL, layer type, visible-by-default flag, source, attribution, update date, and validation/verification notes.
- Provide clear legends and distinguish point, line, polygon, boundary, and hazard layers.
- Do not use color alone to convey verification/hazard state; include text labels or accessible controls.
- Keep map popups accessible and concise; offer a non-map way to read essential feature information.
- Avoid loading all high-detail geometries eagerly if performance suffers. Use bounded datasets, simplification, or lazy loading if justified by measurement.
- Do not rely on runtime network requests to Overpass for every visitor. Pre-fetch, review, version, and serve site-owned static data unless a documented product requirement says otherwise.
- Do not include secrets or private data in committed JSON, logs, or built pages.

## 8. Testing requirements

Tests must enforce the publication policy rather than merely encode the current dataset's statuses. Never write a test that assumes every candidate facility is publishable or that all records must remain unverified forever.

Add/extend tests that verify at least:

Add/extend tests that verify at least:

- Every GeoJSON layer parses and has valid geometry type/coordinates.
- All coordinates are within valid longitude/latitude ranges and in the expected order.
- Feature IDs are unique within a layer.
- Required source/provenance and review metadata exists for publishable features.
- The barangay reference dataset includes all 15 expected codes and the supplied population values sum to `38228` for the stated 2024 POPCEN reference.
- No hall point is serialized as a polygon or marked as a centroid without a calculated centroid from an approved polygon.
- Known contradictions are recorded as `needs_review`/excluded until explicitly resolved.
- Each unresolved blocking review issue causes all affected feature IDs to be excluded from public GIS payloads at build time, regardless of a conflicting `source_verified` value.
- A regression fixture with `verification_status: source_verified` plus an open blocking review issue is still excluded from public output.
- Resolved issues can be published only after a persisted review decision cites evidence; tests must not require a permanent blanket status/count for all candidate records.
- Public map text and counts reflect the publishable subset, and do not claim that coordinates are verified when `location_precision` is approximate or last verification is absent.
- The generated public HTML does not contain excluded facility records or internal review notes.
- Manifest layers marked available resolve to actual emitted data assets and supported renderer handlers; declared-but-missing data fails validation or is explicitly marked unavailable.
- Unreviewed features are not shown in production layers by default.
- Unlocated projects do not receive synthetic coordinates.
- Source or layer download failures do not silently replace existing data with an empty file.
- GIS page renders/works for English, Filipino, and Pangasinan routes as required by the existing site.
- Attribution is present and existing localization/build/lint/tests continue to pass.

If a relevant data claim cannot be tested automatically, document a manual review step rather than pretending the test proves accuracy.

## 9. Git workflow and delivery

- Before editing, report the intended files and an implementation sequence.
- Avoid broad refactors unrelated to GIS.
- Keep changes in small logical commits when requested by the repository workflow.
- Do not modify canonical data from unreviewed remote data as part of a build command.
- Never auto-publish or auto-merge new GIS data without human approval.
- After changes, run relevant tests, the full site build, localization checks, and any GIS validation script; report commands and actual outcomes honestly.
- Update the relevant source registry, GIS plan, README, or data dictionary whenever a new layer is added.
- Summarize which records remain excluded or uncertain and why.

## 10. Definition of done

The first release is done only when the GIS page integrates into the current static site, is usable on mobile, has proper map attribution, uses only sourced/validated geometries, makes uncertainty visible, has a fallback when data is missing, passes relevant tests/build/localization checks, and documents how to update the data. A visually complete map made from unverified or fabricated geographic features is not considered done. The build-time publication gate must be tested against unresolved review blockers, including a fixture that falsely labels a conflicted record as `source_verified`.

## Starting reference links

- PSA/PSGC, Mapandan barangays: https://psa.gov.ph/classification/psgc/barangays/0105528000
- Municipality of Mapandan, Disaster Awareness: https://mapandan.gov.ph/disaster-awareness/
- Municipality of Mapandan, hazard map (published 2 September 2020): https://mapandan.gov.ph/disaster-awareness/mapandan-hazard-map/
- Geoportal Philippines: https://www.geoportal.gov.ph/
- Overpass Turbo documentation: https://dev.overpass-api.de/overpass-doc/en/targets/turbo.html
- OSM attribution/license: https://www.openstreetmap.org/copyright
- Leaflet reference: https://leafletjs.com/reference
- DepEd school masterlist: https://ebeis.deped.gov.ph/beis/reports_info/masterlist
- DOH National Health Facility Registry: https://nhfr.doh.gov.ph/VActivefacilitiesList
