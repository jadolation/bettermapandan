# Implementation Plan: Additional QA Issues

## Context

Addressing 5 remaining issues identified after the previous implementation plan.

---

## Issue 1: Empty `<h3>` in Homepage Municipality Card

**Location:** `src/pages/index.html:112` → generates `index.html:209`

**Root Cause:** Key mismatch in `build.py` locale lookup.

| Locale key in JSON | Lookup in build.py |
|---|---|
| `municipality_founded` | `homepage.municipality_found` |
| `municipality_reestablished` | `homepage.municipality_reestablished` |

The build.py lookup uses `municipality_found` but locale has `municipality_founded` (typo - missing 'd').

**Fix:** Update `build.py:1211-1212` to use correct key names:
```python
"HOMEPAGE_MUNICIPALITY_FOUNDED": t(locale, "homepage.municipality_founded", ""),
"HOMEPAGE_MUNICIPALITY_REESTABLISHED": t(locale, "homepage.municipality_reestablished", ""),
```

**Validation:**
```bash
python3 build.py
grep -A1 'class="icon">01</div>' index.html | head -2
# Should show: <h3>Founded Dec. 28, 1887</h3>
```

---

## Issue 2: search-index.json Loaded on Every Page (INVESTIGATE)

User reports 556KB search-index.json is loaded on every page.

**grep shows only search.html references it:**
- `search.html:223`
- `fil/search.html:223`
- `src/pages/search.html:126`

**Action:** Investigate if there's a second loading mechanism (e.g., script.js loads it, or browser preloads it).

**Validation:**
```bash
# Check script.js for any search-index loading
grep -n "search-index" assets/script.js

# Check if any other files load it
grep -r "search-index" --include="*.js" --include="*.html" . | grep -v "search.html"

# Check base.html for any global script that might load it
grep -n "search" src/partials/base.html
```

If investigation finds no additional loading, mark as N/A (already optimized via lazy fetch).

---

## Issue 3: Inline Styles Contradict README Claim

**Location:** `build.py:322-330` in `_build_photo_html()`

**Current State:** Generates inline `style="..."` on `<figure>`, `<img>`, and `<figcaption>`

**README Claim:** `assets/style.css` has "zero inline styles anywhere in the generated HTML"

**Root Cause:** The `_build_photo_html()` function generates inline styles for:
- figure: `margin: 2rem 0; text-align: center;`
- img: `max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);`
- figcaption: `font-size: 0.875rem; color: #666; margin-top: 0.5rem; font-style: italic;`

**Fix Options:**
1. **Add CSS classes** to `assets/style.css` and use class attributes instead
2. **Update README** to clarify inline styles are used for citizen charter images only

**Recommended:** Option 1 - Add CSS classes `.service-photo-container`, `.service-photo`, `.service-photo-caption`

**Changes:**
1. `assets/style.css` — Add:
```css
.service-photo-container {
  margin: 2rem 0;
  text-align: center;
}
.service-photo {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
.service-photo-caption {
  font-size: 0.875rem;
  color: #666;
  margin-top: 0.5rem;
  font-style: italic;
}
```

2. `build.py:322-330` — Replace inline styles with class references

**Validation:**
```bash
python3 build.py
# Check generated service pages have class instead of style
grep -c 'style=' services/aics.html
# Should be 0 for service photo elements
```

---

## Issues 4 & 5: onclick/onerror Inline Handlers — SKIPPED

Per user decision, inline onclick and onerror handlers are acceptable given the current CSP allows `'unsafe-inline'`. No changes needed.

---

## Execution Order

1. **Issue 1**: Fix locale key mismatch (`municipality_found` → `municipality_founded`)
2. **Issue 2**: Investigate search-index.json loading (confirm or find hidden loading)
3. **Issue 3**: Add CSS classes for service photo inline styles

**Issues 4 & 5 skipped** — inline handlers acceptable given current CSP.

---

## Validation Commands

```bash
# Issue 1
python3 build.py
grep -A1 'class="icon">01</div>' index.html | head -2
# Should show: <h3>Founded Dec. 28, 1887</h3>

# Issue 3
python3 build.py
grep 'style=' services/aics.html | grep -v "font-size\|color\|margin" || echo "No inline styles on service photo"
# Verify no inline styles on service photo elements
```

---

## Open Questions

None remaining — plan is ready for implementation.
