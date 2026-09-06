# Better Mapandan — Codebase Analysis & Cleanup Plan

## Context
An independent transparency portal for Municipality of Mapandan, Pangasinan. Bilingual (EN/FIL) static site built with a custom Python static site generator. The user wants a thorough analysis and will do codebase cleaning later.

---

## Architecture Summary

- **Build:** Python 3-only static site generator (`build.py`, 1,387 lines)
- **Templates:** Custom `{{KEY}}` / `{KEY}` string substitution (two syntaxes used inconsistently)
- **Data:** JSON files for services (90+ entries), legislative (ordinances/resolutions), barangays (15)
- **i18n:** EN at root, FIL under `/fil/` — locales in `locales/en.json` and `locales/fil.json`
- **Styling:** Single 3,171-line CSS file with design token system
- **JS:** Vanilla ~446 lines — nav, weather API, charts, barangay modal, feedback widget
- **Output:** Static HTML committed alongside source (dual-tracking problem)

---

## Issues Found

### Critical

1. **`downloadCSV()` undefined** — `statistics.html:279,297,324` calls `onclick="downloadCSV('...')"` but this function is never defined. Clicking these buttons throws `ReferenceError`.

2. **FIL locale `transparency` key not translated** — `fil.json:9` has `"transparency": "Transparency"` (English). All other nav items are translated.

3. **FIL pages are identical to EN** — `build.py:1331-1334` contains `pass` with a comment `# ... (FIL replacements will be migrated in Phase 2)`. The FIL locale strings are loaded but never applied to page body content.

### High

4. **Placeholder syntax inconsistency** — Source pages use both `{KEY}` (single braces) and `{{KEY}}` (double braces) for template variables. The `fill()` function handles both, but this is confusing and error-prone for contributors.

5. **Emergency bar hardcoded duplicate contacts** — `header.html:1-12` duplicates the same 4 emergency numbers twice to create a continuous ticker scroll effect. Wastes DOM; should use CSS pseudo-elements.

6. **Population data claim inconsistency** — `statistics.html:28` says "PSA Census 2024" with 38,228 residents. PSA's most recent census was 2020 (38,058). The 38,228 figure may be a projection or unofficial estimate, not clearly labeled.

### Medium

7. **`robots.txt` blocks `/support/` but sitemap includes support pages** — The `Disallow: /support/` rule blocks crawling, but `sitemap.xml` references `support/faq.html`, `support/report.html`, etc. from the root (not `/support/`). These are served from root so the Disallow may be unintentional.

8. **Search index (490KB) fetched on every search** — `search.html:124` fetches `assets/search-index.json` via HTTP with no caching headers set. Large payload on each search.

9. **Chart.js loaded on every page** — `base.html:29` includes Chart.js CDN on all pages, but it's only needed on statistics and about pages for population/fiscal charts.

10. **No pre-commit hook** — README instructs committing both `src/` changes AND regenerated HTML. If someone forgets to rebuild, repo has stale output.

11. **`REPO_URL` hardcoded** — In `SITE_CONFIG` dict inside `build.py`, not an environment variable or config file.

12. **No CSS minification** — 62KB CSS served raw. No build step for compression.

### Low

13. **Inline `style` attributes** — `service.html:10,240-248` and `transparency.html` have inline styles that should be CSS classes.

14. **No SRI hashes** — CDN scripts (Chart.js, Lucide, Google Fonts) lack Subresource Integrity hashes.

15. **`__pycache__/` in repo** — Should be in `.gitignore`.

16. **Monolithic `build.py`** — 1,387-line file with no separation of concerns (data loading, page assembly, sitemap, search index, CLI all in one function).

17. **Locale key sprawl** — ~200 `t(locale, "dot.nested.key", "default")` calls all in one function body (`build.py:935-1175`), making additions/error-prone.

18. **No `requirements.txt`** — Only uses Python stdlib, but no pin file exists.

19. **Generated files committed to repo** — Creates dual-tracking problem (source vs. output both in git).

20. **Image compression requires Node.js** — `build.py --compress` generates an inline Node.js script using `sharp`. Not usable on a plain Python environment.

---

## Cleanup Recommendations (Priority Order)

### Phase 1: Fix Critical Bugs
1. Define `downloadCSV()` function in `script.js` or remove the `onclick` attributes
2. Fix `fil.json:9` translation for `transparency` nav item
3. Implement FIL string substitution or remove FIL output entirely until Phase 2

### Phase 2: Address High-Priority Issues
4. Standardize all placeholders to single `{KEY}` syntax (or `{{KEY}}`), update `fill()` accordingly
5. Fix emergency bar to use CSS `content: ""` duplication instead of hardcoded HTML
6. Clarify the "PSA Census 2024" label — either remove the claim or use a proper source attribution

### Phase 3: Technical Debt Reduction
7. Refactor `build.py` into smaller modules (page builder, data loader, sitemap generator)
8. Move `REPO_URL` and other config to environment variables or a `config.json`
9. Add a pre-commit hook that runs `python3 build.py` after `src/` changes
10. Add `__pycache__/` and `*.pyc` to `.gitignore`
11. Add `requirements.txt` (even if just documenting stdlib-only)

### Phase 4: Performance
12. Add `defer`/`async` to Chart.js and Lucide script tags
13. Consider code-splitting: only load Chart.js on statistics/about pages
14. Add HTTP caching headers via hosting config (or a `_headers` file for Netlify)
15. Consider compressing or optimizing the 1.3MB SVG logos

### Phase 5: UI/UX Polish
16. Extract inline `style` attributes to CSS classes
17. Add `prefers-reduced-motion` media query for emergency ticker
18. Add Open Graph meta tags for social sharing
19. Add canonical URL meta tags
20. Implement SRI hashes for CDN resources

---

## Validation Plan

After cleanup:
1. Run `python3 build.py` — verify no errors
2. Run `python3 build.py --verify-translations` — check for remaining untranslated segments
3. Manually verify FIL pages show Filipino content (not English)
4. Click the CSV download buttons on `/statistics.html` — verify they work
5. Run `grep -r "onclick=" src/` to find any other undefined handlers
6. Check generated HTML size (should decrease after inline style extraction)
7. Verify FIL locale file has same number of keys as EN (or document intentional omissions)

---

## Open Questions

1. Should FIL output be fully implemented before cleanup, or should FIL be disabled until Phase 2?
2. Should the build system switch to an established SSG (e.g., Eleventy, Hugo)?
3. Is the 490KB search index acceptable, or should it be split/compressed?
4. Should generated HTML files remain in the repo, or should a build-on-deploy CI pipeline replace them?
