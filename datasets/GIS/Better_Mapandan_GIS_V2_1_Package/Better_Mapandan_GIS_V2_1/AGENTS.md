# AGENTS.md — Better Mapandan GIS V2.1 Operating Rules

**Authority and installation:** Intended as **repository-root `AGENTS.md`** on the `GIS` branch after maintainer review. This copy in the handoff is **not** automatically effective. Before installation inspect any root or nested `AGENTS.md` instructions, including `datasets/GIS/AGENTS.md` **if present**. Do not assume it exists; reconcile conflicts with the maintainer and document the winning policy. Avoid silently superseding existing policies. Read `GIS_IMPLEMENTATION_PLAN_V2_1.md` and inspect target branch at its current commit.

**Status:** Documents reported corrective work; confirms no fresh tests or data approvals by itself.

## Nonnegotiable policies

1. Never fabricate municipal/barangay boundaries, hazard zones, facility positions, route safety, evacuation designations, or spatial precision from text, labels, rough color masks, Plus Codes, or AI inference.
2. Candidate/unvalidated GeoJSON and label anchors are internal research inputs **only**; no public overlay, exposure statistics, legal boundary or navigation endpoints. Keep source geometry null where appropriate.
3. `source_verified` != coordinate accurate, facility identity confirmed, field checked, operational, designated shelter, or publishable. All 16 current facility candidates are reported unpublished. A UI must work with zero approved facilities.
4. Hazard maps are historical/scenario-based. Never claim real-time safety, present evacuation routing as safe, or derive parcel-specific exposure from coarse raster or approximate locations. Always show source, legend, scenario/date and limits.
5. Source availability is not a license: review agency rights, reuse/derivatives, attribution, and downloads independently. If rights unresolved, do not publish derivative.
6. Preserve factual disagreements verbatim with vintage, provenance and `quality_flags`; never silently overwrite authoritative/canonical source fields with historic map transcriptions.
7. Approval is bound to **exact source and derivative bytes and meanings**. Changed SHA-256, CRS, bounds, legend/class meanings, source vintage/scenario, intended claims/use, transformation, uncertainty or unresolved blockers voids approval. Re-review is mandatory.
8. Fail closed at **build**, not only in JS; missing rights/approval/renderer, malformed data, unsafe script encoding, or unpublished attributes must not enter `_site`. Invalid inputs cannot be emitted raw as fallback.
9. Authoritative software baseline to inspect: `_build/gis.py` (current publication policy), `_build/staging.py` (allowlisted `_site` output), GIS build/JS, existing i18n/static fallback. **Do not resurrect the obsolete claim that `_build/pages.py` is the only policy gate**, nor that unsafe inline JSON is unfixed. Verify changes in checked-out commit.
10. Human approval is separate from implementation. An engineer/agent can extract, transform, validate, and recommend; **cannot grant source, rights, location, public-safety, or release approvals on its own**.

## Confirmed-by-maintainer baseline (reverify in branch)

Maintainer reports fail-closed facilities, HTML-safe JSON, approved-only data, static accessible directories, EN/FIL/PAG, OSM initialization and co-location popups, `_site` staging, and 367 passing Python + 9 JS tests. **These are not independently rerun.** Browser visual/CDN testing and blocking CI release gates remain unfinished; 36 broader lint diagnostics reportedly predate the corrective work. Do not redo completed P0 changes unless regression testing shows a defect.

## Separation of duties

- **Research:** extract original claims, dates, classifications, provenance; flag contradictions, no approvals.
- **GIS processing:** candidate vectors/rasters, GCP fitting, validation and reproducibility; no promotion to public.
- **Independent geographic review:** use held-out checkpoints distinct from fitting GCPs, assess geolocation residuals, topology, map scale and source-vintage conflicts.
- **Rights review:** record allowed public display, derivative, hosting/download and attribution.
- **Human publication approver:** sign an immutable derivative, its source and claims, allowed use, accuracy limits, scenario and legend.
- **CI/release:** verify all signatures and exact hashes against `_site`; no self-approval.

## Build and source rules

- Respect existing `_build/gis.py`. Design new ETL modules compatible with it; do not introduce `_build/gis/` beside `_build/gis.py` without refactoring imports, tests and ownership intentionally.
- Do not assume the nested `datasets/GIS/AGENTS.md` still exists. Locate it; if absent, note absence and use confirmed root policy when installed.
- Original images/KMZ and exact provenance in research archive; candidate derivatives outside public output; approved browser assets only in `_site`. Don't add raw research, hidden review notes or approval personal data to public bundles.
- `layers.json` must not advertise data without a real published file and tested type-specific renderer. Available layers have dates, legends, attributions, and explicit limitations.
- All three language variants have localized map controls, empty/failed states and precision terminology. Accessible HTML directory works without map/JS.
- Maintain immutable six-source catalog: PHIVOLCS shaking (Feb 2022: PEIS VI/VII/VIII+), liquefaction poster (Dec 2025 high/moderate/low) vs KMZ file labeled 2024, MPDC 2012 elevation (1,4,8,12,16,20,24,28 m), slope (0–3%,3–8%), soils (four classes), land capability (image A/B; text X). Different vintages and provenance stay separate.
- Preserve historical municipal reference 3291.7520 ha MPDC vs 2459.6652 ha assessor scope; historical 2023 RHU 43722 vs 2024 PSA 38228; slope 86.57/13.43%; soil class sum 2631.981 vs reported 2132.704 ha; capability classes 2132.143 vs municipality 3291.752 ha. No unreviewed calculated areas.
- Review PSGC crosswalk for 15 barangay elevation ranges before canonical join; don't interpret an elevation class range as parcel elevation.

## Required workflow

1. Check current branch/commit/status; inventory applicable AGENTS scopes, `_build/gis.py`, `_build/staging.py`, browser assets, registry, data, tests, CI.
2. State files to modify, exact public-data impact and expected approval needs; avoid modifying unrelated modules.
3. Build candidate data/renderer independently; attach source SHA-256, derivative SHA-256, original/source CRS, output CRS, bounds, transformations and tool versions.
4. For georeferenced imagery separate **fitting GCPs** and **held-out independent accuracy checkpoints**. Record both errors, distribution and intended scale; fitting residuals alone are never proof of accuracy.
5. Obtain independent evidence review, rights decision and named human publication decision covering exact bytes, class legend and intended claim. No missing approval may default true.
6. Run Python/JS tests, GIS approval regressions, Playwright keyboard/mobile/no-JS tests, translations, internal links, and staging allowlist scan. Make deploy depend on these gates.
7. Report statuses individually: `research`, `candidate`, `in_review`, `approved_for_specific_use`, `blocked`, `published`. Only verified approval + tested renderer + staged hashes enable `published`.

## Critical acceptance tests

- Current 16 unapproved facility candidates produce **zero public markers and zero payload entries**; accessible approved-facility directory correctly reports none.
- `</script><script>alert(1)</script>` cannot execute via generated inline data.
- Unsupported renderer or unapproved geometry/raster never yields a selectable public layer.
- Modified derivative hash, changed bounds/CRS/legend/scenario or expired/absent rights blocks stage.
- Missing checkpoint QA blocks any georeferenced overlay's publication.
- PSGC joins require reviewed mapping; labels are not centroids; no fake hazard intersections.
- `_site` allowlist contains no research or internal review files; repeated builds deterministic under pinned environment.
- Browser checks cover map and static directory, desktop/mobile, EN/FIL/PAG, keyboard, popup focus, external tile failure.
- Quality and browser checks are **blocking prerequisites for publishing the exact tested artifact**, not merely separate jobs that may finish after deployment.

## Agent completion report (mandatory)

Report commit, files, source references/hashes, candidate/approved/published changes, explicit human/rights decisions, tests with exact commands/results, screenshots when tested, unavailable data, accuracy and legal limitations, unresolved defects and publication blockers. Never describe an unreviewed source or a passing unit suite as a published, accurate GIS layer.
