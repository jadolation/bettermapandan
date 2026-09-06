# Build Script Refactoring & Asset Optimization Plan

## Context

The `build.py` script has a cyclomatic complexity of 33 in the `build()` function, far exceeding the target of <10. Additionally, assets are not optimized, causing excessive page weight.

## Goals

1. Reduce `build()` cyclomatic complexity to <10 per function
2. Compress citizen charter images (~11MB JPGs)
3. Optimize large SVG files (~1.3MB each)
4. Lazy-load search-index.json (554KB)

---

## Tasks

### Phase 1: Refactor `build()` Function

**Current problem**: The `build()` function (lines 920-1533) handles:
- Locale loading
- Asset base computation
- Language loop (EN/FIL)
- Service page generation
- Legislative page generation
- Static page processing (with header/footer/breadcrumbs/body filling)
- Generated page processing
- Search index building
- CSS minification
- Asset copying
- Sitemap generation

**Solution**: Extract logic into focused helper functions.

#### Step 1.1: Extract header/footer building

Create `build_header()` and `build_footer()` functions that accept `(locale, asset_base, is_fil, rel_path)` and return the filled header/footer HTML.

**New functions:**
```python
def build_header(locale: dict, asset_base: str, is_fil: bool, rel_path: Path) -> str:
def build_footer(locale: dict, asset_base: str, is_fil: bool, rel_path: Path) -> str:
```

#### Step 1.2: Extract asset base computation

Create `compute_asset_base(rel_path: Path, is_fil: bool) -> str`.

#### Step 1.3: Extract language switcher URL building

Create `build_lang_switcher_urls(rel_path: Path, is_fil: bool) -> tuple[en_url, fil_url]`.

#### Step 1.4: Extract breadcrumb building

Create `build_breadcrumbs(locale: dict, rel: Path, page_title: str) -> str`.

#### Step 1.5: Extract body placeholders resolution

The massive `fill(body, {...})` call at lines 1074-1314 with 150+ locale keys should become `resolve_body_placeholders(body, locale, asset_base)`.

#### Step 1.6: Extract page assembly

Create `assemble_page(base, title, description, header, body, footer, lang_attr) -> str`.

#### Step 1.7: Extract static page processing

Create `process_static_page(page_path, locale, base, header_raw, footer_raw, page_hero_raw, is_fil) -> tuple[html, search_entry]`.

#### Step 1.8: Extract generated page processing

Create `process_generated_page(rel_path, body_content, page_meta, page_hero_meta, locale, base, header_raw, footer_raw, page_hero_raw, is_fil) -> tuple[html, search_entry]`.

#### Step 1.9: Refactor `build()` to orchestration

```python
def build() -> None:
    generate_barangays()
    en_locale = load_locale("en")
    fil_locale = load_locale("fil")
    
    base = read_base_template()
    header_raw, footer_raw, page_hero_raw = read_partials()
    
    clean_fil_output()
    
    for lang_code, locale, out_root, is_fil in LANGUAGES:
        svc_pages = generate_services_and_legislative(locale, is_fil)
        search_entries = []
        count = 0
        
        # Process static pages
        for page_path in get_static_pages():
            html, entry, page_count = process_static_page(...)
            write_page(out_root, page_path, html)
            search_entries.append(entry)
            count += page_count
        
        # Process generated pages
        for rel_path, content in svc_pages.items():
            html, entry, page_count = process_generated_page(...)
            write_page(out_root, rel_path, html)
            search_entries.append(entry)
            count += page_count
        
        write_search_index(search_entries)
    
    minify_assets()
    copy_assets_to_fil()
    generate_sitemap()
```

**Complexity targets after refactor:**
| Function | Target Complexity |
|----------|-------------------|
| `build` | 5-7 |
| `process_static_page` | 6-8 |
| `process_generated_page` | 6-8 |
| `build_header` | 4-6 |
| `build_footer` | 4-6 |
| `resolve_body_placeholders` | 5-7 |

---

### Phase 2: Image Compression

The `compress_images()` function exists but is not integrated into normal builds.

**Task**: Ensure `--compress` flag works and documents usage.

1. Verify `compress.mjs` script is written correctly
2. Document: `python3 build.py --compress`
3. Consider adding a `python3 build.py --optimize-only` flag for just image compression

**Expected reduction**: 100+ JPGs at ~100KB each = ~10MB → ~4MB (60% reduction with quality 82)

---

### Phase 3: SVG Optimization

**Problem**: `logo.svg` and `logo-no-white.svg` are ~1.3MB each.

**Root cause**: SVGs likely contain embedded raster images or unnecessary metadata.

**Solution**: 
1. Use `svgo` to optimize SVGs: `npx svgo assets/logo.svg --multipass`
2. Or manually inspect and remove embedded rasters
3. Replace with properly exported vector SVGs

**Expected reduction**: 1.3MB → ~50-100KB

---

### Phase 4: Lazy-load Search Index

**Problem**: `search-index.json` (554KB) loads on every page.

**Solution**: 
1. Modify `base.html` to NOT load `search-index.json` by default
2. Modify `script.js` to fetch it only when search modal opens
3. Show loading indicator while fetching

**Files to modify:**
- `src/partials/base.html` - remove search-index script
- `assets/script.js` - add lazy load on search open

---

## Validation

1. Run `time python3 build.py` - should complete in <30s
2. Calculate cyclomatic complexity with AST parser - all functions should be <10
3. Verify `--compress` reduces citizens-charter JPGs by 50%+
4. Verify search still works after lazy loading
5. Check SVG file sizes are <200KB

## Open Questions

1. Should we integrate `--compress` into normal build, or keep as separate step?
   - **Recommended**: Keep as separate `python3 build.py --compress` but ensure it runs before deployment

2. Do we need to preserve the exact HTML output, or is whitespace-only change acceptable?
   - **Assumption**: Output must be byte-for-byte identical (except for compressed images) - refactoring should not change HTML output
