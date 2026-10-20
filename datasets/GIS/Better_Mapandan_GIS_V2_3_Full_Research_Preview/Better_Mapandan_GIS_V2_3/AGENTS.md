# AGENTS.md — Better Mapandan GIS V2.3 Operating Rules — Full Research Preview + GitHub PR Approvals

**Authority and installation:** Intended as **repository-root `AGENTS.md`** on the `GIS` branch after maintainer review. This copy in the handoff is **not** automatically effective. Before installation inspect any root or nested `AGENTS.md` instructions, including `datasets/GIS/AGENTS.md` **if present**. Do not assume it exists; reconcile conflicts with the maintainer and document the winning policy. Avoid silently superseding existing policies. Read `GIS_IMPLEMENTATION_PLAN_V2_3.md` and inspect target branch at its current commit.

**Status:** Documents reported corrective work; confirms no fresh tests or data approvals by itself.

## V2.3 research-preview authorization (read before implementation)

**Explicit authorization:** Coding agents MAY build and test the entire GIS application and all feasible layer renderers with existing experimental datasets in a **local-only or genuinely access-controlled** research preview. Human *publication* approval is NOT required to implement a renderer, explore historical rasters, inspect polygons, show all 16 candidate facilities with uncertainty labels, or build GIS UI. This does NOT authorize source use that violates rights nor publication of candidates. Keep HTML/script injection protection and integrity tests active in both modes.

- Implement two explicit configurations: `GIS_MODE=research_preview` to a separate `_preview_gis/` output and `GIS_MODE=public` (default) to the standard approved-only `_site` staging. Treat names as proposed until integrated into existing build CLI. Reject unrecognized modes; no blanket bypass flags.
- Never load research payloads via client-only hiding in production. Prevent them from entering public artifacts, static asset copies, search indexes, or GitHub Pages upload; remember public Git repository content is accessible regardless of Pages.
- Preview may display experimental municipal outline, label anchors (as *label anchors*, never centroids), color-segmentation polygons, PHIVOLCS/map images, roads/places, 16 facility candidates and evidence-backed project relationships where inputs actually exist and can be parsed. Mark experimental source vintage, location precision, rights/approval state. Avoid pretending an unsupported map is rendered.
- Deliver full explorer UX now: grouped layers, map controls, responsive layout, search/filter, feature detail panel, confidence/provenance, selected features, Project Explorer links, localized EN/FIL/PAG strings and accessible no-JS fallback. Approval delays must not block this engineering work.
- Preview must have visible persistent **RESEARCH PREVIEW — NOT FOR PUBLIC USE** treatment and use localhost or real authentication. `robots.txt`, secret URLs, and watermarks are not security controls.
- Experimental hazard/exposure analysis is internal debugging only. No safe-route, emergency-ready, parcel-precision or official claims. No synthetic geometry, facility status or project coordinates.
- Include positive preview tests and **negative public-leak tests** covering renamed/unapproved assets, HTML payloads, JSON, downloaded maps, search, all locales, dynamic builds and exact tested `_site` release.

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
- **CI/release:** verify authorized decisions under the chosen protected-ledger model and exact hashes against `_site`; do not claim cryptographic signature checks unless implemented; no self-approval.

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
5. Open GitHub PR(s) with evidence and candidate data. Obtain independent evidence review, rights decision and designated human publication approval under protected branch rules. Record exact approved bytes, legend, claims, scope, and GitHub review reference. No missing approval may default true. A PR merge or `approved: true` flag alone is insufficient.
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

## GitHub PR approval protocol (selected V2.2 workflow)

- Use GitHub PRs instead of an admin dashboard. A coding agent may author source inventories, candidate artifacts, QA reports, approval *requests*, schema/CI code and PR descriptions. **It may not perform human GitHub Approve actions, impersonate reviewers, forge signatures, self-approve candidate layers, or weaken branch/ruleset protection.**
- Keep a versioned approval schema and protected approval ledger separate from runtime `src/data/gis/layers.json` and candidate datasets. Respect any existing facility-specific approval gate; migrate only with tests and maintainer approval.
- A designated human rights reviewer must confirm scope of permitted reuse, hosting, derivative work and attribution. A geographic reviewer must assess source identity, accuracy and any independent georeferencing checkpoints. The publication approver must authorize the particular source/derivative hashes, legend, uncertainty and intended claims.
- Configure and **verify** GitHub branch/ruleset protection, relevant CODEOWNERS rules, required checks, and review restrictions on the intended deployment branch. CODEOWNERS without enforced rules is advisory. A PR approval is an attributable review, **not a cryptographic signature** and not independent proof of rights/accuracy.
- An untrusted PR branch must never confer authorization by editing approval JSON or CI scripts. The release job must consume a trusted approval decision, check reviewer authority/provenance against configured controls and validate source/derivative bytes. Prevent bypass through renaming assets or modifying manifests.
- A public GitHub repository is public even outside `_site`. Do not commit confidential reviewer notes, restricted source files, personal contact details or unpublished permissions; store sensitive evidence privately and reference it safely.
- Approval lifecycle: `candidate`, `in_review`, `approved`, `published`, `blocked`, `revoked`; transition only after required evidence and authorization. Changed source, derivative, bounds, CRS, legend, scenario, public claim, rights or accuracy evidence invalidates approval. Revoke via an auditable reviewed change and remove from next release.
- Candidate images and the 16 currently unapproved facility points may be developed in **local or access-controlled** previews only. Do not deploy an open-to-the-public "preview" with release gates disabled.
- Use `.github/PULL_REQUEST_TEMPLATE/gis-data.md` to request approvals; do not auto-check human attestations. Refer to `GIS_IMPLEMENTATION_PLAN_V2_3.md` section 3A for roles, schema, CI negative tests, and maintainer steps.

## V2.3 completion standard

Report preview and public behavior separately. Explicitly count candidate previews and publication-approved layers (including zero), identify unavailable source/renderer items, and record both build output directories and public-leak test results. The engineering agent may report an implemented GIS feature even when its layer is research-only, but must never report it as an approved public dataset.
