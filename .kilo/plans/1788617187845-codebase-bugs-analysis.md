# Codebase Bug Analysis - BetterMapandan

## HIGH SEVERITY

### 1. Legislative Page Missing Hero Section
**Files:** `src/templates/legislative.html`, `build.py`
**Lines:** legislative.html:4-6 (front matter), build.py:1325-1431

**Problem:** The `legislative.html` template has front matter defining `hero_eyebrow`, `hero_heading`, and `hero_lede`:
```yaml
hero_eyebrow: Sangguniang Bayan
hero_heading: Legislative Documents
hero_lede: A comprehensive database of municipal ordinances...
```

However, the build code for generated pages (lines 1325-1431) does NOT process or render these hero fields. Static pages (lines 929-1034) properly assemble hero sections using `page_hero.html` template when hero fields exist, but generated pages (services, legislative) skip hero assembly entirely.

**Root cause:** `generate_legislative()` returns only the body HTML and metadata. It doesn't return the hero metadata. The page assembly loop at lines 1418-1431 has a comment "no hero for generated pages" but the legislative template actually needs one.

**Fix:** Modify `generate_legislative()` to return hero metadata alongside body HTML and metadata, then build the hero section when assembling the legislative page.

---

### 2. Land Area Discrepancy
**Files:** `locales/en.json`, `src/data/legislative.json`
**Lines:** en.json:52,93 | legislative.json:7

```
locales/en.json:52  "municipality_desc": "...Covering 30.00 square kilometres..."
src/data/legislative.json:7  "land_area": "32.92 km²"
```

The homepage/municipality description says 30.00 km² but the legislative page shows 32.92 km². These should be consistent.

**Fix:** Decide which is correct and update all references.

---

### 3. Modal Focus Management - `previouslyFocused` Not Restored on Escape Key
**File:** `assets/script.js`
**Lines:** 514, 527-531

```javascript
closeBtn = overlay.querySelector(".barangay-modal-close");  // Line 514 - re-assigned!
```

The `closeBtn` variable is reassigned at line 514 after the initial assignment at line 375. When `close()` is called via the Escape key handler at line 516, the `closeBtn` click listener at line 533 still references the original button (from line 375), not the re-assigned one at line 514. However, this is actually correct because the original `closeBtn` is captured in the closure.

More critically: `previouslyFocused` is only restored if `previouslyFocused.focus` exists. If the triggering element was removed from DOM, focus won't return.

---

### 4. Hardcoded Population Chart Data
**File:** `assets/script.js`
**Lines:** 282-285

```javascript
data: {
  labels: ["1903", "1918", "1939", "1948", "1960", "1970", "1980", "1990", "2000", "2010", "2020", "2024"],
  datasets: [{
    label: "Population",
    data: [4198, 6049, 7286, 9836, 13065, 16653, 20094, 25622, 30775, 34077, 38058, 38228],
```

This data is hardcoded in JavaScript rather than sourced from JSON or locale files.

---

## MEDIUM SEVERITY

### 5. Unused Locale Key Definition
**File:** `build.py`
**Line:** 1097 (approximately)

`GOVERNMENT_DEPT_COL_CONTACT` is defined in `en.json`:
```json
"dept_col_contact": "Contact"
```

But this locale key is NOT referenced in `build.py` and NOT used in `src/pages/government.html`. The government table uses hardcoded "Contact" instead.

**Fix:** Either use the locale key in the template or remove the unused key from `en.json`.

---

### 6. Unused `escAttr` Function
**File:** `assets/script.js`
**Lines:** 13-16

```javascript
function escAttr(str) {
  if (str == null) return "";
  return String(str).replace(/"/g, "&quot;");
}
```

This function is defined but never called anywhere in the codebase.

---

### 7. Filipino Locale - `transparency` Not Translated
**File:** `locales/fil.json`
**Line:** 9

```json
"transparency": "Transparency",
```

Should be translated to Filipino (e.g., " Transparency " or "Kabatiran").

---

### 8. Filipino Locale - `emergency.label` Not Translated
**File:** `locales/fil.json`
**Line:** 15

```json
"label": "Emergency",
```

Should be "Emergency" or translated to Filipino.

---

### 9. Feedback Widget - Null Check Missing
**File:** `assets/script.js`
**Lines:** 558-574

```javascript
var feedback = document.getElementById("service-feedback");
if (feedback) {
  var feedbackService = document.querySelector(".hero h1");
  var serviceName = feedbackService ? feedbackService.textContent.trim() : "";
  var feedbackKey = "feedback_" + serviceName.replace(/[^a-z0-9]/gi, "_");
  if (localStorage.getItem(feedbackKey)) {
    feedback.querySelector(".feedback-buttons").style.display = "none";
    feedback.querySelector(".feedback-thanks").style.display = "block";
  }
  feedback.querySelectorAll("button").forEach(function(btn) {  // Could throw if feedback is null
```

While there's an `if (feedback)` check, inside the block at line 567, if `feedback-buttons` or `feedback-thanks` don't exist, `feedback.querySelector(...)` returns null and setting `.style.display` silently fails.

---

### 10. Barangay Modal - Close Handler Re-assignment
**File:** `assets/script.js`
**Lines:** 375, 514, 533

```javascript
closeBtn = overlay.querySelector(".barangay-modal-close");  // Line 375 - initial assignment
// ... modal built and appended to body ...
closeBtn = overlay.querySelector(".barangay-modal-close");  // Line 514 - RE-ASSIGNED!
closeBtn.addEventListener("click", close);  // Line 533 - uses SECOND assignment
```

The click handler at line 533 is attached to the reassigned `closeBtn` (line 514), which should correctly reference the button inside the overlay. This works but is confusing.

---

### 11. Weather API - Missing Wind Gust Data
**File:** `assets/script.js`
**Lines:** 101-102

The weather widget requests 15 parameters but Open-Meteo free tier may not include all. The API call requests:
```javascript
"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum"
```

Some of these may not be available on the free tier, causing silent failures.

---

## LOW SEVERITY

### 12. Section Anchors Missing from Service Pages
**File:** `build.py`
**Lines:** 1451-1457

Service pages (generated) don't include `section_anchors` in the search index, while static pages do (lines 1315-1322).

---

### 13. Generated Service Pages Search Index Entry Missing Description
**File:** `build.py`
**Lines:** 1451-1456

```javascript
entry = {
    "title": rel.stem.replace("-", " ").title(),
    "url": url,
    "description": "",  // Always empty for generated pages
    "body": plain_body,
}
```

Static pages have `meta["description"]` but generated service pages use empty string.

---

### 14. CSS Minification Regex - Inefficient Whitespace Handling
**File:** `build.py`
**Lines:** 798-805

```python
CSS_WHITESPACE_RE = re.compile(r"\s+")
...
css = CSS_WHITESPACE_RE.sub(" ", css)
```

This collapses all whitespace to single spaces inside CSS values, which may not preserve single-space contexts properly. Also `CSS_LEADING_RE` uses `re.MULTILINE` but `CSS_TRAILING_RE` doesn't use it, causing inconsistent behavior.

---

### 15. `generate_sitemap()` URL Encoding
**File:** `build.py`
**Lines:** 773-774

```python
en_url = f"{base_url}/{quote(path, safe='/')}"
fil_url = f"{base_url}/fil/{quote(path, safe='/')}"
```

This correctly handles spaces and special characters in sitemap URLs. This is actually CORRECT.

---

### 16. `fill()` Template Function - Both Placeholder Styles Replaced
**File:** `build.py`
**Lines:** 126-131

```python
def fill(template: str, values: dict) -> str:
    for key, value in values.items():
        str_value = str(value) if value is not None else ""
        template = template.replace("{{" + key + "}}", str_value)
        template = template.replace("{" + key + "}", str_value)
    return template
```

Both `{{VAR}}` and `{VAR}` styles are replaced. This means if a template accidentally has both styles for the same key, they get the same value. Template consistency could be improved by picking one style.

---

### 17. `strip_html()` - HTMLParser Fallback
**File:** `build.py`
**Lines:** 134-151

The `TextExtractor` class is defined inside the function. If `parser.feed()` throws an exception, it falls back to regex-based stripping. The regex `r"<[^>]+>"` is much less accurate than proper HTML parsing and could produce incorrect plain text.

---

## INFORMATIONAL

### 18. No Automated Tests
The codebase has no test suite. Running `python3 build.py` is the only validation.

### 19. Build Artifacts Copied to FIL Directory
**File:** `build.py`
**Lines:** 1470-1477

```python
if assets_src.exists():
    if assets_dst.exists():
        shutil.rmtree(assets_dst)
    shutil.copytree(assets_src, assets_dst)
```

This copies ALL assets including `barangay-data.js` and `search-index.json` to the Filipino output directory. While `search-index.json` is for the EN version, it doesn't cause issues since it's not loaded.

### 20. Missing CRLF Line Ending Check
Some files in the repository may have CRLF (`\r\n`) line endings which can cause issues with edit commands and bash operations. The `src/partials/base.html` was reported to have CRLF issues in prior session.

---

## SUMMARY

| Priority | Count | Key Issues |
|----------|-------|------------|
| High | 4 | Legislative hero missing, land area mismatch, modal focus, hardcoded chart data |
| Medium | 6 | Unused locale key, unused function, Filipino translations, null checks, weather API |
| Low | 5 | Section anchors missing, search index issues, CSS regex, fill() style |
| Info | 5 | No tests, build artifacts, etc. |

**Note:** Lucide icons issue has been resolved (icons are now visible).

## RECOMMENDED ACTIONS

1. **High:** Fix legislative page missing hero section - modify `generate_legislative()` to return hero metadata and build hero during page assembly
2. **High:** Fix land area discrepancy (decide between 30.00 vs 32.92 km²)
3. **High:** Move population chart data to JSON/locale file
4. **Medium:** Add Filipino translations for `transparency` and `emergency.label`
5. **Medium:** Remove or use `GOVERNMENT_DEPT_COL_CONTACT` locale key
6. **Low:** Add `section_anchors` support for generated service pages
