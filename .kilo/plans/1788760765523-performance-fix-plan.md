# Performance Fix Implementation Plan

## Context

Lighthouse analysis of https://jadolation.github.io/bettermapandan/ shows:
- **Performance Score: 65** (target: 90+)
- **LCP: 13.4 seconds** (target: ≤2.5s)
- **Total Page Weight: 4.6 MB** (target: <2 MB)

### Root Causes Identified

1. **SVG files contain embedded base64 PNG images** (1.3MB each)
   - `assets/logo.svg` and `assets/logo-no-white.svg` are 1.3MB each
   - They wrap a 1254x1254 PNG seal image in SVG format
   - This is extremely inefficient - just use PNG/WebP directly

2. **Hero image uses `loading="lazy"`** 
   - `logo-no-white.svg` is the LCP element but has `loading="lazy"`
   - Missing `fetchpriority="high"` attribute

3. **`luyan.png` is 1.8MB** and not optimized
   - Could be converted to WebP (saves ~1.5MB)

---

## Task 1: Fix Hero Image Loading

### Steps

1. **Edit `src/partials/page-hero.html`** (line 2):
   ```html
   <!-- BEFORE -->
   <img class="hero-rays" src="{{ASSET_BASE}}/assets/logo-no-white.svg" alt="" aria-hidden="true" />
   
   <!-- AFTER -->
   <img class="hero-rays" src="{{ASSET_BASE}}/assets/logo-no-white.svg" alt="" aria-hidden="true" fetchpriority="high" />
   ```

2. **Edit `src/pages/index.html`** (line 6):
   - Add `fetchpriority="high"` to the hero img tag

3. **Edit `src/pages/search.html`** (line 6):
   - Add `fetchpriority="high"` to the hero img tag

4. **Edit `src/pages/statistics.html`** (line 6):
   - Add `fetchpriority="high"` to the hero img tag

### Validation
- Rebuild site with `python3 build.py`
- Verify generated HTML has `fetchpriority="high"` on hero images
- No `loading="lazy"` attribute should be present on these images

---

## Task 2: Optimize SVG Files

### Problem
The SVG files contain embedded base64 PNG data (~1.3MB each). This is wasteful because:
- SVG is meant for vector graphics, not raster images
- Base64 encoding increases size by ~33%
- The "SVG" is just a wrapper for a raster PNG

### Solution Options

**Option A (Recommended): Replace with optimized PNG**
1. Extract the embedded PNG from the SVG (already done - they're the same seal)
2. Convert to WebP for better compression
3. Replace SVG references with WebP references
4. Keep both logo.svg (as actual vector) and logo-no-white.webp for hero

**Option B: Use actual SVG with optimized logo**
1. Create a proper vector SVG of the seal
2. This requires redesign - out of scope for this fix

### Implementation (Option A)

1. **Extract PNG from SVG data**
   - The embedded PNG in the SVG is the municipal seal (1254x1254)
   - Save as `assets/municipal-seal.png`

2. **Convert to WebP** (using sharp)
   ```javascript
   // compress.mjs addition
   const sealPng = await sharp("assets/municipal-seal.png")
     .resize(400, 400, { fit: 'contain' }) // No need for 1254px
     .webp({ quality: 85 })
     .toBuffer();
   fs.writeFileSync("assets/municipal-seal.webp", sealPng);
   ```

3. **Update hero references to use WebP**
   - Change `logo-no-white.svg` to `municipal-seal.webp` in page-hero.html and pages
   - Use proper `img` tag with alt text

### Validation
- File size of `municipal-seal.webp` should be < 50KB
- Hero section displays correctly
- No broken images

---

## Task 3: Optimize luyan.png (Hero Card Background)

### Current State
- File: `assets/luyan.png`
- Size: 1,768 KB
- Usage: Background image in card components

### Implementation

1. **Convert to WebP** (using sharp):
   ```javascript
   const luyanWebp = await sharp("assets/luyan.png")
     .resize(1200, null, { withoutEnlargement: true })
     .webp({ quality: 80 })
     .toBuffer();
   fs.writeFileSync("assets/luyan.webp", luyanWebp);
   ```

2. **Update CSS to reference WebP** (in `assets/style.css`):
   - Add WebP fallback support via CSS

3. **Or update HTML references** if background is set inline

### Validation
- File size < 200KB
- Image displays correctly
- Mobile/responsive displays correctly

---

## Task 4: Update build.py to Include New Optimization

### Steps

1. **Extend `compress_images()` function** to also:
   - Extract PNG from SVG (or handle separately)
   - Convert logo-no-white.svg to WebP
   - Convert luyan.png to WebP
   - Generate proper WebP variants

2. **Update file references** in templates if using WebP

### Code Location
- `build.py` lines 906-1000: `compress_images()` function

---

## Task 5: Rebuild and Redeploy

1. Run: `python3 build.py --compress`
2. Commit changes to Git
3. Push to GitHub
4. Wait for GitHub Pages rebuild
5. Run Lighthouse again to verify improvement

---

## Files to Modify

| File | Change |
|------|--------|
| `src/partials/page-hero.html` | Add `fetchpriority="high"` |
| `src/pages/index.html` | Add `fetchpriority="high"` |
| `src/pages/search.html` | Add `fetchpriority="high"` |
| `src/pages/statistics.html` | Add `fetchpriority="high"` |
| `build.py` | Extend `compress_images()` for WebP conversion |
| `assets/style.css` | Optional: WebP fallback support |

---

## Expected Outcome

| Metric | Before | Target | Expected |
|--------|--------|--------|----------|
| LCP | 13.4s | ≤2.5s | ~2s |
| Page Weight | 4.6MB | <2MB | ~1.2MB |
| Performance Score | 65 | ≥90 | ~92 |

### Estimated Savings
- `logo-no-white.svg` (973KB) → `municipal-seal.webp` (~30KB): **-943KB**
- `luyan.png` (1,768KB) → `luyan.webp` (~180KB): **-1,588KB**
- Total: **~2.5MB reduction**

---

## Open Questions

1. Should we keep both SVG files for download (higher quality) and use WebP for display?
2. Should we also optimize the other hero images (Pandan.jpg, plaza.jpg)?
3. Do we need to support browsers that don't support WebP?

---

## Validation Commands

```bash
# After build
python3 build.py --compress

# Check file sizes
ls -lh assets/*.webp assets/luyan.* assets/logo*.svg

# Redeploy
git add -A && git commit -m "perf: optimize images for Lighthouse improvement" && git push

# Re-test (after GitHub Pages rebuild)
# Visit: https://jadolation.github.io/bettermapandan/
# Run Lighthouse
```
