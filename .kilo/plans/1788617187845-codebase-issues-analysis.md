# Better Mapandan - Codebase Issues & Remediation Plan

## Executive Summary

Analysis identified **45 issues** across the codebase:
- **5 Critical** - Security vulnerabilities, personal data exposure
- **11 High** - XSS vectors, memory leaks, data integrity
- **12 Medium** - Error handling, accessibility, performance
- **17 Low** - Code quality, minor issues

---

## Critical Issues (Fix Immediately)

### C1: Personal Data Exposure in Public Repository
**Files:** `src/data/barangays.json`, `assets/barangay-data.js`

Barangay official personal data (emails, phone numbers, names) is publicly accessible in the repo.

**Remediation:**
- Option A: Remove personal contact info from public JSON, keep only work contacts
- Option B: Move personal data to separate private data file not committed
- Option C: Hash/redact personal data, use placeholder references

**Decision needed:** Which approach?

### C2: XSS via innerHTML in Barangay Card Grid
**File:** `assets/script.js:296`

```javascript
card.innerHTML = "<h4>" + name + '</h4>...' + d.pop2024 + ...;
```

All card data inserted via innerHTML without escaping.

**Fix:** Use `textContent` for text nodes, DOM methods for structured HTML.

### C3: XSS via innerHTML in Barangay Modal
**File:** `assets/script.js:360-385`

```javascript
popEl.innerHTML = "<strong>2024 Population:</strong> " + data.pop2024 + ...
contactDiv.innerHTML = contactHtml; // built from data.facebook, data.phone
kagawadDiv.innerHTML = kagawadHtml; // built from kagawads array
```

**Fix:** Already fixed in Phase 9 for history field - need to extend to all fields.

### C4: CSP Allows 'unsafe-inline'
**File:** `src/partials/base.html:6`

```html
<meta http-equiv="Content-Security-Policy" content="... script-src 'self' 'unsafe-inline' ...">
```

Defeats XSS protection. Inline scripts needed for:
- Mobile nav toggle
- Language switcher onclick handlers
- Accordion toggles
- Feedback widget buttons

**Fix:** Move inline handlers to external JS file or use nonce-based approach.

### C5: No SRI for CDN Scripts
**File:** `src/partials/base.html:29-30`

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://unpkg.com/lucide@0.460.0/dist/umd/lucide.min.js"></script>
```

**Fix:** Add `integrity` and `crossorigin` attributes with SRI hashes.

---

## High Priority Issues

### H1: Memory Leak - Modal Event Listener Not Removed
**File:** `assets/script.js:420-421`

```javascript
document.addEventListener("keydown", function handler(e) {
    if (e.key === "Escape") { close(); document.removeEventListener("keydown", handler); }
```

Handler only removed on Escape. Click overlay/close button leaves handler attached.

**Fix:** Remove handler in all close paths (overlay click, close button, page navigation).

### H2: Weather API No Null Checks
**File:** `assets/script.js:86-102`

```javascript
var current = data.current;  // Could be undefined
var code = current.weather_code;  // Throws if current undefined
```

**Fix:** Add existence checks before accessing properties.

### H3: Chart.js Loaded on All Pages
**File:** `src/partials/base.html:30`

Chart.js is ~60KB but only used on statistics, about, and index pages.

**Fix:** Load Chart.js only on pages that need it, or defer loading.

### H4: Inconsistent Phone/Email Field Handling
**File:** `src/data/barangays.json`

Examples:
- `"phone": "N/A"` vs `"phone": ""` vs missing field
- `"email": ""` vs `"email": "N/A"` vs missing

**Fix:** Standardize schema - use `null` for missing, "N/A" for explicitly unavailable.

### H5: Inconsistent Contact Field Names
**File:** `src/data/barangays.json`

- Kagawads use `email`/`contact`
- Officials use `email`/`contact` 
- But some entries have `""`, some have missing keys

**Fix:** Add JSON schema validation to build process.

### H6: Carousel startAuto() Called Unconditionally
**File:** `assets/script.js:222`

```javascript
if (region) { ... }
startAuto();  // Called even if region is null
```

**Fix:** Guard `startAuto()` with region existence check.

### H7: No Error Handling for Chart.js Init
**File:** `assets/script.js:248`

```javascript
new Chart(ctx, { ... });
```

**Fix:** Wrap in try/catch.

### H8: Mixed HTTP/HTTPS External Links
**File:** Generated HTML files

Some external links use `http://` instead of `https://`.

**Fix:** Normalize all external links to HTTPS.

### H9: Weather API No Offline Fallback
**File:** `assets/script.js:60-162`

API failure shows error with no cached/static fallback.

**Fix:** Store last successful response in localStorage, display as fallback.

### H10: Duplicate clearTimeout
**File:** `assets/script.js:87,149`

`clearTimeout(timeout)` called twice in success path.

**Fix:** Remove duplicate at line 149.

### H11: Language Switcher URL Fragility
**File:** `assets/script.js:507`

```javascript
switchUrl = "/fil" + location.pathname;
```

No validation of pathname.

**Fix:** Use URL API for safe path manipulation.

---

## Medium Priority Issues

### M1: Focus Not Trapped in Modal
**File:** `assets/script.js:420-430`

Tab cycles within modal but focus not strictly trapped - could tab to background.

**Fix:** Implement proper focus trap (already partially implemented, needs hardening).

### M2: getCurrentLang() Fragile
**File:** `assets/script.js:9`

```javascript
return location.pathname.indexOf("/fil/") !== -1 ? "fil" : "en";
```

**Fix:** Use DOM `lang` attribute instead of path checking.

### M3: build.py sys.exit() in Production
**File:** `build.py:110,118`

Abrupt termination without cleanup.

**Fix:** Raise custom exception instead.

### M4: No Data Freshness Indicators
**File:** `src/data/barangays.json`

No `last_updated` field to indicate data currency.

**Fix:** Add `last_updated` timestamp to all data files.

### M5: Language Suggestion Banner Potential Issues
**File:** `assets/script.js:474-518`

URL construction without sanitization.

**Fix:** Validate and sanitize locale storage values.

### M6: lucide.createIcons() No Error Handling
**File:** `assets/script.js:150,165`

**Fix:** Wrap in try/catch.

### M7: Service Pages Load Unnecessary Assets
**File:** `src/templates/service.html`

Chart.js loaded but not used on service pages.

**Fix:** Defer Chart.js loading or conditionally load.

### M8: No Input Validation in Report Form
**File:** `support/report.html`

**Fix:** Add client-side validation.

### M9: Inconsistent Field Naming
**File:** `src/data/barangays.json`

- `punong_barangay` in JSON vs `punong` in generated JS
- `kagawads` vs `officials` schema differences

**Fix:** Document schema and add validation.

### M10: No Schema Validation in Build
**File:** `build.py`

**Fix:** Add JSON schema validation for all data files.

### M11: Timeline Potential Race Condition
**File:** `assets/script.js:206-222`

**Fix:** Add guards for undefined track/slides.

### M12: Accessibility - Focus Restoration Edge Cases
**File:** `assets/script.js:416`

**Fix:** Check element still in DOM before focusing.

---

## Low Priority Issues

### L1: Hardcoded CDN Version Numbers
### L2: No prefetch/preload hints
### L3: CSS animation not respecting prefers-reduced-motion
### L4: Emergency bar keyboard navigation
### L5: No print styles
### L6: Mobile action bar visibility
### L7: Weather error messages not localized
### L8: Font fallback limited
### L9: Duplicate clearTimeout redundancy
### L10: Translation incompleteness tracking

---

## Implementation Plan

### Phase 1: Security Critical (Immediate)
1. [ ] Fix C2: XSS in barangay card grid (line 296)
2. [ ] Fix C3: Complete XSS fix for modal all fields
3. [ ] Fix C5: Add SRI hashes to CDN scripts
4. [ ] Plan C1: Personal data handling decision
5. [ ] Fix C4: CSP unsafe-inline (requires JS restructuring)

### Phase 2: Memory & Error Handling
1. [ ] Fix H1: Modal event listener memory leak
2. [ ] Fix H2: Weather API null checks
3. [ ] Fix H7: Chart.js init error handling
4. [ ] Fix H10: Remove duplicate clearTimeout
5. [ ] Fix M6: lucide.createIcons error handling

### Phase 3: Data Integrity
1. [ ] Fix H4: Standardize phone/email field handling
2. [ ] Fix H5: Standardize contact schema
3. [ ] Add schema validation to build.py
4. [ ] Add last_updated to data files

### Phase 4: Performance
1. [ ] Fix H3: Conditional Chart.js loading
2. [ ] Fix M7: Service page asset optimization

### Phase 5: Accessibility & Polish
1. [ ] Fix M1: Hardened focus trap
2. [ ] Fix M2: lang attribute-based detection
3. [ ] Add print styles
4. [ ] Fix L3: prefers-reduced-motion

---

## Open Questions

1. **C1 (Personal Data):** How should personal official data be handled?
   - Remove from public repo?
   - Move to private data store?
   - Keep but hash/anonymize?

2. **C4 (CSP):** Are inline event handlers essential or can they be moved to external JS?
