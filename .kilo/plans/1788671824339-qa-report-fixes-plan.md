# Implementation Plan: QA Report Fixes

## Context

The QA analysis identified issues in priority order. This plan addresses them sequentially.

## Priority 1: Alt Text for Service Charters (HIGH)

**Current state:** `_build_photo_html` generates `alt="{name} Reference"` — a generic placeholder.

**Expected state:** Descriptive alt text like "Citizens Charter for {Service Name}" or similar.

**Changes:**
- `build.py:315` — Modify `_build_photo_html()` to use descriptive alt text
- Alt format: `"Citizens Charter for {service_name}"` (from `svc.get('name', '')`)
- Also update `figcaption` to be more descriptive

**Validation:**
```bash
# Rebuild and check generated alt attributes
python3 build.py
grep -o 'alt="[^"]*Reference"' services/*.html | head -10
```

---

## Priority 2: Ruff Lint Errors (MEDIUM)

**Current state:** 13 errors, 8 auto-fixable.

**Changes:**

1. **Auto-fix 8 issues:**
   ```bash
   ruff check build.py --fix
   ```

2. **Manually fix remaining 5:**
   - `BLE001` line 154: Replace blind `except Exception:` with specific exception handling
   - `DTZ011` line 817: Use `datetime.datetime.now(tz=...).date()` instead of `datetime.date.today()`
   - `PLW1510` line 966: Add `check=False` to `subprocess.run()` or handle return code
   - `F841` line 441: Remove unused `template_body` variable
   - `F841` line 528: Remove unused `fiscal` variable

3. **Add ruff configuration** (`ruff.toml`):
   ```toml
   target-version = "py39"
   line-length = 100
   select = ["E", "F", "I", "BLE", "PLW", "DTZ", "FURB"]
   ignore = ["E501"]  # line-too-long handled separately
   ```

**Validation:**
```bash
ruff check build.py  # Should return 0 errors
```

---

## Priority 3: verify_translations Complexity (MEDIUM)

**Current state:** Complexity 13 (Grade C), 80 lines.

**Expected state:** Complexity ≤ 10 (Grade A).

**Changes:** Split into smaller functions:
- `verify_translations()` — orchestrator (complexity 3)
- `_strip_tags_for_comparison()` — tag stripping logic
- `_extract_text_segments()` — segment extraction
- `_compare_file_pair()` — per-file comparison
- `_build_allowlist()` — allowlist definition (moved to module level)

**Validation:**
```bash
radon cc build.py -a -s | grep verify_translations
# Should show Grade B or lower
```

---

## Priority 4: CDN SRI (MEDIUM)

**Current state:** CDN scripts in `src/partials/base.html` lack proper SRI hashes.

**Expected state:** `integrity` and `crossorigin` attributes on CDN scripts.

**Note:** The QA report claimed scripts were "without integrity attributes" but the actual base.html already has:
- Chart.js: `integrity="sha256-0e2326c6868072..." crossorigin="anonymous"`
- Lucide: `integrity="sha256-GyLGwEocabda..." crossorigin="anonymous"`

**Changes (verify):**
- Confirm SRI hashes are current for Chart.js 4.4.0 and Lucide 0.460.0
- If stale, update to latest SRI hashes from jsdelivr/unpkg

**Validation:**
```bash
# Check base.html has integrity attributes
grep 'integrity=' src/partials/base.html
```

---

## Priority 5: Type Annotations (LOW)

**Current state:** 6 mypy errors due to missing type annotations.

**Changes:** Add gradual type annotations:
- `build.py:88` `load_locale()` → `-> dict`
- `build.py:101` `t()` → `-> str`
- `build.py:117` `parse_page()` → `-> tuple[dict, str]`
- `build.py:177` `generate_services()` → add all type hints
- `build.py:1364` `build_search_entry()` sort key fix

**Validation:**
```bash
mypy build.py  # Should have 0 errors
```

---

## Priority 6: SEO Enhancements (LOW)

**Current state:** Missing Open Graph tags, canonical URLs, JSON-LD.

**Changes:**
1. **Open Graph tags** — Add to `src/partials/base.html`:
   ```html
   <meta property="og:title" content="{{TITLE}}">
   <meta property="og:description" content="{{DESCRIPTION}}">
   <meta property="og:type" content="website">
   <meta property="og:url" content="{{CANONICAL_URL}}">
   ```

2. **Canonical URLs** — Add `{{CANONICAL_URL}}` placeholder to base template

3. **JSON-LD** — Add `GovernmentOrganization` schema to base template:
   ```html
   <script type="application/ld+json">
   {
     "@context": "https://schema.org",
     "@type": "GovernmentOrganization",
     "name": "Municipality of Mapandan",
     "url": "https://bettermapandan.org",
     "address": { ... },
     "areaServed": "Mapandan, Pangasinan, Philippines"
   }
   </script>
   ```

**Validation:**
```bash
grep -c 'og:' src/partials/base.html  # Should be > 0
```

---

## Priority 7: search-index.json Size (LOW)

**Current state:** 544 KB loaded on search page.

**Expected state:** Lazy loading or pagination.

**Changes (if needed):**
- Confirm search-index.json is loaded with `defer` or at bottom
- Consider splitting into chunks if page load is slow

**Validation:**
```bash
# Check search page loads index lazily
grep -A5 'search-index' assets/script.js
```

---

## Execution Order

1. Alt text fixes
2. Ruff auto-fix + manual fixes
3. Add ruff.toml
4. verify_translations refactor
5. SRI verification
6. Type annotations (optional)
7. SEO enhancements (optional)
8. search-index optimization (optional)

---

## Risks & Open Questions

1. **Alt text change** — Will affect ~101 generated service pages. Ensure output matches expectations.

2. **verify_translations refactor** — Must preserve existing logic (substring matching, allowlist, output format).

3. **SRI hashes** — If CDN versions change, SRI hashes must be regenerated.

4. **JSON-LD schema** — User confirmed `GovernmentOrganization` is appropriate. ✅ Resolved.
