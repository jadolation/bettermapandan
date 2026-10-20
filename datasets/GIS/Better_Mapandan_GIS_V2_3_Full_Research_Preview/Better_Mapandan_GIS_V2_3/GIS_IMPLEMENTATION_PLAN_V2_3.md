# Better Mapandan GIS — Implementation Specification V2.3 — Full Research Preview + GitHub PR Data Approvals

**Date:** 19 October 2026  
**Repository:** `jadolation/bettermapandan` · working branch `GIS`  
**Status:** Revised specification based on the maintainer-reported corrective implementation; this document does not independently certify the latest branch, review decisions, or public layers.  
**Supersedes:** `GIS_IMPLEMENTATION_PLAN_V2_2.md` for forward implementation. Historical V2 extraction remains traceable; no candidate geometries are approved by this document.  
**Approval workflow decision:** GitHub pull requests with structured evidence/approval records (no admin dashboard). No current records are automatically approved.  
**Development policy decision:** Implement all feasible GIS engine and interface features NOW using research-only datasets in an isolated development preview. Publication approval is NOT a prerequisite for renderer coding or preview tests. Public export remains approval-gated.  
**Companion:** `AGENTS.md` in this handoff; install authoritative instructions at repository root after policy reconciliation.

## 0. V2.3 decisive objective and two-mode contract

**Primary objective: deliver the full GIS application architecture and usable research workspace now, even when zero features are approved for public publication.** Build/preview approval is not a waiver of source integrity, HTML safety, licensing, or production release checks. Never require a publication approval merely to implement a renderer, create a QA candidate, or test a locally rendered map.

| Source / feature | RESEARCH_PREVIEW (local or authenticated) | PUBLIC (strictly released) |
|---|---|---|
| Traced municipality outline | Render as uncertain **candidate**, visually dashed, inspectable | Exclude until geometry/source/rights and specific-claims approval |
| 15 barangay text-label anchors | Render as **cartographic labels only**; not centers or destinations | Never use as centroids, boundaries, routing or exposure anchors |
| Slope/color land-capability polygons | Render with experimental warning + QA/debug controls | Only independently georeferenced, reviewed approved derivative |
| PHIVOLCS historical maps/KMZ | Inspect raw images and extracted raster/KML in QA mode, disclaim scenario/version | Only registered, rights-cleared, approved overlays |
| All 16 facility candidates | Preview with status, provenance, location-precision badges, co-location handling | Publication-approved subset **possibly zero** |
| OSM road/places extracts | Preview and test styles, selection, search, rendering | Only rights/attribution-reviewed published assets |
| Projects and barangay joins | Preview *evidence-supported* join with confidence; unresolved records listed with no map location | Only approved public point geometry or source-supported nonspatial links |
| Experimental spatial calculations | Internal debug results with assumptions/uncertainty; **not safety determinations** | Only with sufficiently accurate approved geometry and validated method |
| Hazard-aware evacuation routing | **Not built as a safety feature**; no promise of safe routes | Require separate hazard/routing validation and official operational source |
| Search, layer controls, details, localization, accessible directory | Fully develop and test against both non-empty and zero-data fixtures | Deploy with **approved** data or honest empty states |

### Configuration / isolation (requirements, not claims of existing commands)

- Implement an explicit, typed build mode `GIS_MODE=research_preview|public` (proposed contract; choose final documented command names during integration), with default **public** and an allowlisted parser that rejects unknown values. Do **not** implement a global `BYPASS_APPROVAL` or `DISABLE_SECURITY` toggle.
- Research builds go only to a separate directory, e.g. `_preview_gis/`, **never** `_site/`; ignore preview directory in production staging, Pages upload, sitemap/search generation, and deploy jobs. The normal public build must not read preview-only layers into any emitted files.
- Research mode is **not authentication**. Serve on localhost for individual work, or require a genuinely access-controlled environment for collaborators. Do not rely on `robots.txt`, random URLs, client flags, or a watermark as access control. A public GitHub repo is public to anyone who can read committed candidate files, even when absent from `_site`.
- Keep the existing `_build/gis.py` publication gate and `_build/staging.py` allowlist. Implement preview as an isolated projection of candidate data, **not** an alternative permissive path in the public export gate.
- Research-mode source access is limited to datasets actually acquired and permitted for internal use. Lack of public redistribution permission doesn't automatically grant internal usage rights; keep restricted originals outside public Git and respect source conditions.
- Expose mode visibly in UI (persistent `RESEARCH PREVIEW — NOT FOR PUBLIC USE` banner, dataset status and precision per feature). The public page must never show the preview banner or hidden research data.
- Use different explicit asset manifests/data paths per mode, with typed layer states (`candidate`, `in_review`, `approved`, `blocked`, `revoked`, `unavailable`) separate from `renderable_in_preview` and `publishable`. No state magically implies positional accuracy.

### Full implementation authorized before publication approvals

1. Full-height responsive Leaflet explorer: grouped layer sidebar; search across available nonspatial and spatial records; feature list, filters, selected-feature detail drawer, mobile sheet and keyboard controls.
2. Typed, extensible loader registry for point, line, polygon, inspected raster/KML overlay and authorized WMS, with lazy load, loading/error/empty states, provenance and legends. No dead controls for unavailable datasets.
3. Research preview of six-map extraction artifacts, existing PHIVOLCS KMZ source investigations, all 16 candidate facilities, OSM roads and places, and existing project entities **only where the actual files and evidence support the representation**. Map label anchors are expressly not coordinates for public geography.
4. Barangay search and historical attributes via reviewed or explicitly tentative PSGC crosswalk; null geometry means show a nonspatial record without a synthetic `flyTo` target.
5. Safe, contextual Project Explorer links with evidence/confidence; do not plot ambiguous project points or automatically geocode to barangay label anchors.
6. EN/FIL/PAG labels; accessibility, no-JS reference directories; visible source/as-of/rights/position precision warnings; tested map/CDN/tile failure behavior.
7. Internal spatial-analysis tooling may validate transforms and inspect candidates, but suppress meaningful hazard-exposure counts, safe navigation, and official-sounding spatial conclusions until quality standards are met.

### Acceptance criteria and executable gates

- A locally reproducible **research** build visibly renders all *available and technically parseable* candidate sources with transparent limitation labels; unsupported KMZ/raster remains an explicit not-yet-ready entry, not a silent fake overlay.
- A **public** build produced from the *same checkout* contains zero unapproved features in all HTML/JS/JSON/GeoJSON/images/tiles/manifests/search indexes/sitemaps/downloads; exact bytes/paths scanned, not filename substrings only. Changing candidate data must not change public asset hashes except explicitly permitted public metadata.
- CI negative test plants an unapproved marker, geometry, renamed image and malicious HTML/JS field: public artifact remains free of all; script data is escaped; previews may display sanitized details only.
- CI checks preview does **not** overwrite `_site` and the Pages workflow accepts only a tested `_site` artifact. Verify a deliberately failing gate prevents deploy.
- Browser tests cover research with multiple layers, public with **zero approved facilities**, EN/FIL/PAG, mobile/desktop, keyboard, no-JS and external basemap failure. Build/test commands and final paths must be added to repo documentation after implementation.
- No approved layer required for functional frontend completion. Each public layer separately follows immutable GitHub PR approval and rights/accuracy review in §3A.

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

Maintain a reviewable private source registry, derivative registry, and approvals ledger (suggest `src/data/gis/registry/` for published-safe metadata, `datasets/GIS/review/` for internal decisions). A published manifest is mechanically derived, never self-authorizing. Approval will be conducted through GitHub pull requests, with maintainer-reviewed records and blocking validation; see Section 3A. Suggested paths must be reconciled with `_build/gis.py` and `_build/staging.py` before code changes; do **not** create `_build/gis/` next to `_build/gis.py` without an intentional migration.

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

No `approved` value may appear merely because a candidate path exists. CI checks the full binding against **real current bytes**, protected review ledger, schema, and rendered interface. Any missing requirement blocks export. The example contains placeholders and is deliberately unpublishable.


## 3A. Chosen approval mechanism: GitHub pull requests (implement this; no dashboard)

**Decision:** Use GitHub PRs as the human review UI and Git-tracked machine-readable approval ledger as the release input. This is a proposed workflow, not a statement that the necessary GitHub settings or CI are already configured. A GitHub review means an identified GitHub user reviewed the change; it is **not** a cryptographic signature, legal permission, geographic field verification, or proof of data accuracy.

### Roles and authority

- **Submitter / agent:** creates a feature branch, gathers original source citations and hashes, prepares a candidate derivative and QA evidence; submits PR. The agent **must not** write an approval decision or change repository protection to grant itself authority.
- **Geographic reviewer:** checks source identity, positional accuracy and independent checkpoints; records a review finding with evidence. For simple point/reference layers, document the layer-appropriate alternative to raster checkpoints.
- **Rights reviewer:** documents the agency's terms or explicit permission for display, transforms, hosting, attribution and downloads. Unknown rights means **blocked**, not implicit permission.
- **Designated publication approver:** reviews the completed evidence and explicitly accepts an immutable set of bytes, legends and claims for a particular use. Approval should preferably be independent of the author; if one maintainer performs multiple roles, record that limitation plainly rather than claiming independent review.
- **Release automation:** checks the approval contract, trusted review path, hashes and output; never constructs missing human approvals.

### Suggested repository files (adapt existing structures rather than overwriting)

```text
.github/
  CODEOWNERS                         # GIS approvals / review ledger owners
  PULL_REQUEST_TEMPLATE/gis-data.md  # standardized human checklist
src/data/gis/
  approvals/schema-v1.json           # versioned schema; created in implementation phase
  approved-layers/                   # approved records only; do not put candidate assets here
  layers.json                        # existing manifest; preserve existing runtime fields
  review/                             # existing facility-review data, not an approval by itself
datasets/GIS/
  sources/                            # public-safe provenance inventory, where appropriate
  candidates/                         # research only; accessible on public GitHub if committed!
  qa/                                 # public-safe QA summaries only
```

**Confidentiality:** The repository is public. `datasets/GIS/` is NOT private simply because `_site` excludes it. Never commit confidential permissions, restricted files, addresses, reviewer personal information beyond intentional GitHub identities, or private source material. Store restricted evidence in an appropriately access-controlled system and commit only safe references/decision metadata. If the public repo is not suitable, keep the underlying approval ledger in a protected private repository or use GitHub environments/checks with a documented secure linkage. Do not assume CODEOWNERS or branch rules are enabled.

### Proposed PR workflow

1. **Prepare candidate PR** against `GIS` (or the chosen protected integration branch): include source URL and source SHA-256, derivative SHA-256, map date vs print/revision date, license/rights evidence, spatial QA, intended display claims, attribution and limitations. Candidate assets remain unapproved; public site still shows zero approved facilities if none has approval.
2. **Technical review:** run source/geometry/unit tests and separate independent registration checkpoints; reviewers record QA verdict. Confirm status is not inferred from `source_verified`.
3. **Rights review:** record exact public use permitted; show an explicit negative or unresolved decision if evidence is lacking.
4. **Publication approval PR:** propose an approval record binding exact source and derivative hashes and all safety-critical metadata. Require the designated approver's GitHub approval of the PR and documented acceptance of the claims/rights and applicable caveats. No approval can be inferred from merge alone.
5. **CI revalidation:** validate approval against exact files, review ledger provenance, current source/version, no revocation/expiry, renderer, output paths and compiled `_site` assets. Reject modifications to approved bytes or claims without renewed approval.
6. **Merge and release:** require branch/ruleset protection for the deployment branch, required status checks, relevant CODEOWNERS reviews, disabled direct/bypass pushes except tightly controlled break-glass, and enforce required review after new pushes. Deploy **the exact staged artifact that passed checks**, not a separately rebuilt unchecked tree.
7. **Withdraw/revoke:** submit a PR changing approval to `revoked` (or removing it via an audited revocation record), require gating tests to ensure associated public assets disappear in next deploy, document emergency takedown procedure and rollback. Avoid a window in which the old release continues to be represented as current after revocation.

**Trust model:** Choose a *protected-ledger GitHub review model* first. Configure repository access and branch rules that constrain who can merge changes to approval files. `CODEOWNERS` helps direct review but is not authorization by itself; branch rules must require code-owner review. CI must not trust `approved: true` in a branch PR as proof of approval. Verify decision provenance using permitted GitHub review/branch context, or maintain a separately protected, already-approved ledger consumed by release jobs. No fabricated cryptographic signatures; add actual signed attestations only if explicitly implemented and tested.

### Machine-readable approval contract (schema v1 proposal)

The runtime `layers.json` is NOT an approval registry. Introduce a distinct versioned approval schema; project it to runtime metadata only after validation. Example **candidate template** (unapproved by design):

```json
{
  "schema_version": "1.0",
  "layer_id": "historic-slope-reference",
  "status": "candidate",
  "source": {
    "id": "mapandan-mpdc-slope-map",
    "sha256": null,
    "document_url": null,
    "data_date": null,
    "print_date": null
  },
  "derivative": {
    "path": null,
    "sha256": null,
    "format": "raster",
    "crs": null,
    "bounds": null,
    "processing_version": null
  },
  "legend_revision": null,
  "claims_revision": null,
  "rights": {"status": "pending", "evidence_reference": null},
  "qa": {"status": "pending", "report_reference": null},
  "publication": {
    "decision": "pending",
    "approved_by": null,
    "approved_at": null,
    "review_reference": null,
    "allowed_uses": [],
    "expires_at": null,
    "revoked_at": null
  }
}
```

The production schema must require a complete immutable claim/legend/rights/registration manifest (or its deterministic hash), validate each field by layer type, enforce valid transitions (`candidate` → `in_review` → `approved` → `published`; any state → `blocked`/`revoked`), and reject stale approvals. The JSON above is a planning example, **not a usable approval bypass**. Validate agreement with actual existing `_build/gis.py` facility approval format before implementing this schema.

### Automated safeguards and negative tests

- PR from an untrusted author adding `approved: true` with no authorized reviewer **cannot publish**.
- A previously approved derivative changed by one byte fails publishing.
- Changed source version/date, map bounds, CRS, legend, scenario, accuracy limits, public wording, or permitted reuse invalidates the approval.
- Approved review metadata with no staged file, or a staged unapproved renamed file, fails.
- Unauthorized change to approval registry or workflows fails branch policy; exercise a test PR and confirm the deployment is blocked.
- Revoked/expired approval removes the related output from the next artifact; no source-only leak in HTML/JSON/search assets/downloads.
- CI differentiates *request to approve* from *approval by an authorized person*; report current GitHub review status and protected decision provenance.

### What the maintainer actually does in GitHub

1. Open the GIS data PR and inspect its **Files changed**, source links, screenshots/QA report, and evidence checklist.
2. Read both the geographic and rights reviewer conclusions. Verify the proposed visual claims match what the evidence supports.
3. If authorized to approve and satisfied, use GitHub **Review changes → Approve** (or request changes). This is a review action, not necessarily final publication authorization unless the protected workflow records the corresponding designated decision.
4. After required reviewers and checks succeed, merge the approval PR into the protected branch. Confirm the release workflow verifies the approved record and stages only eligible files.
5. For unvalidated images, candidate polygons and all 16 currently unapproved facilities, **do not approve publication** solely because they appear on a government website or work in the preview map.

If the repository has only one maintainer, some branch protection configurations may make independent approval impossible. Configure appropriate collaborator roles or retain the layer in review until credible review can occur; do not silently relax safety requirements to make the button available.

## 4. Deployment and CI release contract

Set a **blocking** dependency chain: source/schema tests → GIS data/approval tests → Python integration build → JavaScript/runtime tests → headless real-browser smoke and accessibility checks → staging integrity/allowlist/security scan → deployment of the **same verified `_site` artifact**. PR checks and production release should both run the required gates. Ensure a failed gate prevents publication; report external-tile/CDN outages separately from application JS errors. Keep artifacts/hash manifests for release audit.

Tests must assert: 0 unapproved facility markers AND no forbidden facility payload; 15 barangay reference entries (independent of polygon availability); script-injection strings inert; exact output paths and no research/reviewer files; manifest truth vs actual assets/renderer; rejected/changed derivative SHA blocked; unsupported/unknown CRS blocked; source/license missing blocked; missing/changed legend blocked; independent checkpoints required for registered layers; no synthesized polygons from text anchors; accessible no-JS directories and translations; map/list and controls in Playwright. Capture screenshot diffs without making pixel-perfect snapshots the sole pass criterion.

## 5. Engineering work packages (remaining)

| Phase | Scope | Release acceptance |
|---|---|---|
| P0.1 reconcile policy/baseline | Root-scoped `AGENTS.md`, old `datasets/GIS/AGENTS.md` existence/conflict, current `_build/gis.py`/`_build/staging.py`, tests | One explicit authority; no outdated assertions |
| P0.2 gate tests and PR approval | CI dependencies, protected GitHub review ledger/CODEOWNERS, Playwright, approval schema and checksums | Intentional failing tests block deployment |
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

## V2.3 decision record

- **Selected:** GitHub pull-request approvals and protected machine-readable approval decisions.
- **Not selected:** custom GIS admin/review dashboard.
- **Not permitted:** global bypass of publication checks or agent self-approval.
- **Preview:** full frontend and layer-engine implementation proceeds immediately with research-only inputs in local or genuinely access-controlled environments; no data-publication approval is needed for coding/testing, and research bytes never enter `_site`.
- **Baseline:** completed corrective work is preserved, not re-implemented; future statuses require fresh verification.

### V2.3 release sequencing addendum

**Parallel tracks:** (A) Develop the full zero-data-safe explorer, all feasible candidate renderers, search, filtering and Project Explorer linking **now**; (B) acquire/verify originals, source dates, rights and georeferencing; (C) implement trusted PR ledger/CI to promote individual layers. Block neither A nor B while waiting for layer publication approval. Do **not** treat finishing track A as permission to publish track B's research data.
