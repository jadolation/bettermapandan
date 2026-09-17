# Better Mapandan

An independent transparency portal for the Municipality of Mapandan, Pangasinan, built under the [BetterGov.ph](https://bettergov.ph/) BetterLGU initiative.

**Live at:** [bettermapandan.org](https://bettermapandan.org) — deployed via GitHub Pages with a Hostinger-registered domain.

---

## What this is

Better Mapandan is a static, client-rendered transparency site covering:

- **1,000+ services** across 13 categories (business permitting, civil registry, health, education, etc.)
- **277 procurement contracts** with PhilGEPS tender data
- **45 DPWH projects** with maps and status tracking
- **11 years of COA audit reports** (2014–2024)
- Dual-language: English at root, Filipino under `/fil/`

Total page count: **202 pages** (101 EN + 101 FIL).

---

## Repository structure

```
build.py                        Thin entry point → _build/orchestrator.main()
_build/                         Build system package
  config.py                     Paths, site config, section anchors, front-matter regex
  locales.py                    i18n loader + t() helper
  templates.py                  HTML template engine (parse_page, fill, strip_html, etc.)
  assets.py                     Asset minification, image compression, sitemap, llms.txt
  lint.py                       Translation verification
  generators/
    services.py                 Generates services/, services/*/ index pages from src/data/services.json
    legislative.py              Generates legislative/ from src/data/legislative.json
    dpwh.py                     Generates transparency DPWH/infrastructure sections
    procurement.py              Generates transparency procurement tables + homepage data
    barangays.py                Generates barangay data, comparison script, councils table
src/
  partials/
    base.html                   <head> + <body> shell with {{TITLE}}, {{DESCRIPTION}}, {{HEADER}}, {{BODY}}, {{FOOTER}}, {{LANG_ATTR}}, {{CANONICAL_URL}}, {{ASSET_BASE}}
    page-hero.html              Hero banner partial (eyebrow, heading, lede)
    header.html                 Emergency bar + site nav (single source of truth)
    footer.html                 Site footer, includes {{REPO_URL}}
  pages/
    index.html                  Homepage (front matter + body)
    about.html                  Municipality overview
    government.html             Executive, legislative, departments, contacts
    statistics.html             Demographics, economy, fiscal data
    transparency.html           Budget, audits, procurement, COA projects
    search.html                 Search hub + report form
    support/
      faq.html                  Frequently asked questions
      privacy.html              Privacy policy
      terms.html                Terms of use
      accessibility.html        Accessibility statement
      report.html               Report incorrect info form
      sitemap.html              Sitemap
  templates/
    service.html                Template for individual service pages
    services-directory.html     Template for services index
    legislative.html            Template for legislative section
  data/
    services.json               Service directory (~1,000 entries, 13 categories)
    legislative.json            Ordinances, resolutions, issuances
    procurement.json            PhilGEPS contract records (~277)
    dpwh.json                   DPWH contract records (~45)
    audit-reports.json          11 years of COA opinion & findings data
    barangays.json              33 barangay profiles (population, households, officials)
    transparency-csv.json       Supplemental CSV data for charts
    schemas.py                  JSON Schema validators for procurement, DPWH, barangays
    _utils.py                   Data extraction and normalization helpers
    extract_procurement.py      Procurement data extraction script
    extract_dpwh.py             DPWH data extraction script
    generate_dpwh_seed.py       DPWH seed data generator
assets/
  css/                         34 modular CSS partials (tokens.css, reset.css, layout.css, nav.css, hero.css, cards.css, tables.css, services.css, legislative.css, procurement.css, search.css, responsive.css, etc.)
  js/
    script.js                   Mobile nav, language switcher, weather widget, history carousel, barangay modals, accordions, feedback widget, Lucide icons
    stats.js                    Statistics charts (population, economy, fiscal)
    transparency.js             Transparency page interactions
    services.js                 Services directory logic
    legislative.js              Legislative filters
    search.js                   Client-side full-text search
    search-index.json           Pre-built search index (auto-generated at build)
    common.js                   Shared utilities
    transparency-charts.js      Chart.js instances for transparency section
    procurement-table.js        Procurement table filters/sorting
    leaflet-map.js              Leaflet map for DPWH projects
    report.js                   Report form logic
  data/                         Static data bundles for JS consumption
  logos/                        Brand assets (logo.svg, logo-no-white.svg)
  officials/                    Elected official portraits
  history/                      Historical photos (WebP)
  projects/                     Project thumbnail images
locales/
  en.json                      English UI strings (~678 keys)
  fil.json                      Filipino UI strings (~678 keys)
datasets/                       Raw research and extraction sources
.github/
  workflows/
    quality.yml                 Lint (ruff), complexity (radon), i18n parity, build, link checks
    lighthouse.yml              Lighthouse CI on push/PR
    lighthouse-production.yml   Weekly production Lighthouse monitor
  actions/
    setup-python-build/         Composite action: Python deps + build
    setup-lighthouse/           Composite action: Node + Lighthouse setup
```

---

## How it works

1. `build.py` loads EN and FIL locales from `locales/`.
2. Static pages in `src/pages/` are parsed for front matter and body.
3. Programmatic generators expand service pages, legislative sections, DPWH maps, and procurement tables from `src/data/*.json`.
4. All pages are assembled with `base.html`, `header.html`, and `footer.html`.
5. Locale strings are injected via `t()` calls, resolved against `locales/en.json` and `locales/fil.json`.
6. Output is written to root (EN) and `fil/` (FIL).
7. `search-index.json` is regenerated from all rendered page content.
8. `sitemap.xml` and `llms.txt` are generated for SEO/AI discovery.

Build output directory structure (what actually gets served):

```
index.html                     Homepage (EN)
services/                      Services directory (EN)
  [category]/                  Category pages (13)
    [service]/                 Individual service pages (1,000+)
government/                    Government page (EN)
legislative/                   Legislative page (EN)
statistics/                    Statistics page (EN)
transparency/                  Transparency page (EN)
search/                        Search page (EN)
support/                       Support pages (EN)
  faq, privacy, terms, accessibility, report, sitemap
fil/                           Filipino mirror of everything above
assets/                        CSS, JS, images (shared)
sitemap.xml                    XML sitemap
llms.txt                       LLM-readable site digest
```

---

## Editing content

### Page copy

Edit `src/pages/*.html` (for static pages) or `src/data/*.json` (for programmatic content such as services, procurement, legislative records, and barangay data). Run `python3 build.py` to regenerate.

Page front matter format:

```
---
title: Browser tab title
description: Meta description
---
<body content here — already inside <main> or equivalent>
```

### UI strings

Edit `locales/en.json` and `locales/fil.json`. The build system does not enforce key parity automatically; run `python3 check_i18n.py` or `python3 build.py --verify-translations` to check.

### Styles

`assets/css/` is organized by component. Edit `tokens.css` for design tokens (`--green-deep`, `--gold`, `--red-flag`, etc.) — changing a token re-themes the whole site.

### Scripts

`assets/js/script.js` is the main entry point. Feature-specific logic lives in dedicated files (`search.js`, `services.js`, `transparency-charts.js`, etc.).

---

## Commands

```bash
# Full build (EN + FIL)
python3 build.py

# Image optimization only (mozjpeg + WebP conversion)
python3 build.py --compress

# Translation linting (EN vs FIL rendered output)
python3 build.py --verify-translations

# i18n key parity check
python3 check_i18n.py
```

Image optimization (`--compress`) pipeline:

- **JPG compression** — citizens-charter photos (mozjpeg, quality 70)
- **PNG compression** — history photos (quality 60, compression level 9)
- **Hero images → WebP** — `luyan.webp`, `Pandan.webp`, `plaza.webp` (quality 80, max-width 1200)
- **History PNGs → WebP** — `assets/history/*.png` converted to WebP

Excluded from compression (must remain SVG):

- `assets/logo.svg` — uses `<mask>` + `feColorMatrix` filter pipeline
- `assets/municipal-seal.svg` — embedded PNG with SVG filter rendering

Alternatively: `node optimize-images.mjs` for standalone image optimization.

---

## Data schemas

`src/data/schemas.py` provides JSON Schema validators for:

- `procurement.json` — PhilGEPS contract records
- `dpwh.json` — DPWH infrastructure contracts
- `barangays.json` — Barangay profiles and council data

Validation runs automatically during `build.py` if `jsonschema` is installed:

```bash
pip install -r requirements.txt   # jsonschema>=4.10
python3 build.py
```

---

## Code quality

```bash
# Lint (ruff)
ruff check .

# Cyclomatic complexity (radon) — target: 0 functions above threshold
radon cc . -nd

# Maintainability index (radon) — target: Grade A/B across all modules
radon mi .
```

These run on every push and pull request in CI.

---

## CI/CD

Three GitHub Actions workflows run on every push/PR to `main` or `master`:

### 1. Code Quality & Build Checks (`.github/workflows/quality.yml`)

- Lint with `ruff`
- Cyclomatic complexity with `radon cc`
- Maintainability index with `radon mi`
- i18n parity check with `check_i18n.py`
- Full site build
- Oversized SVG check (>100KB, brand assets excluded)
- Broken link check with Lychee

### 2. Lighthouse CI (`.github/workflows/lighthouse.yml`)

Runs on every push and pull request:

1. Sets up Python 3.11 + Node.js 22
2. Builds the site (`python3 build.py`)
3. Starts a local server on port 9001
4. Runs Lighthouse CI against 11 URLs:
   - Homepage, services directory, business-permit service, government, legislative, statistics, transparency, search, report, about, and one Filipino service page
5. Asserts thresholds from `.lighthouserc.json`

### 3. Production Lighthouse Monitor (`.github/workflows/lighthouse-production.yml`)

- Schedule: every Monday at 08:00 UTC
- Manual trigger available
- Runs Lighthouse against 7 live URLs on `bettermapandan.org`
- Uploads reports to temporary public storage

Lighthouse thresholds (from `.lighthouserc.json`):

| Metric | Threshold |
|---|---|
| Performance | >= 0.50 (warn) |
| Accessibility | >= 0.95 (error) |
| Best Practices | >= 0.90 (warn) |
| SEO | 1.0 (error) |
| FCP | <= 2,000ms (warn) |
| LCP | <= 2,500ms (warn) |
| CLS | <= 0.1 (warn) |
| TBT | <= 300ms (warn) |

---

## Client-side search

The site uses a pre-built `assets/js/search-index.json` (generated at build time) and `assets/js/search.js` for full-text search across all pages. No server-side search infrastructure is required.

---

## Deploying

The site is deployed via **GitHub Pages with GitHub Actions** (`.github/workflows/pages.yml` builds with `python3 build.py` and deploys the artifact). The custom domain `bettermapandan.org` is registered through **Hostinger** and configured with DNS A records pointing to GitHub Pages.

Generated output (`index.html`, section folders, `services/`, `fil/`, `sitemap.xml`, `style.min.css`, `search-index.json`, `*.min.js`) is **not committed** — it is rebuilt on every push. Run `python3 build.py` locally to preview.

Any static host works — run `python3 build.py`, then deploy the root `.html` files plus `assets/`, `locales/`, `fil/`, and top-level files (`sitemap.xml`, `robots.txt`, `CNAME`).

### GitHub Pages

Settings → Pages → **Source: GitHub Actions**. Custom domain configured via Hostinger DNS. Deployment runs automatically on every push to `main` via `pages.yml`.

### Other hosts

- **Netlify / Vercel**: set the build command to `python3 build.py` and `/` as the publish directory.

### Before first deploy

1. **Update `REPO_URL`** in `_build/config.py` to your actual repo URL. This flows into the footer's "Source Code" link on every page.
2. **Verify data.** All data was compiled from public sources (Wikipedia, Provincial Government of Pangasinan, `mapandan.gov.ph`, COA, PhilGEPS, DPWH Transparency Portal) as of August 2026. Before launch, cross-check names, numbers, and figures directly against official sources.
3. **Set custom domain.** Update `CNAME` file content if your domain differs.

---

## Contributing

This project is part of the BetterLGU initiative. If you want to contribute:

1. Fork and clone the repo.
2. Make your changes in `src/` or `locales/`.
3. Run `python3 build.py` to preview locally (generated output is git-ignored — commit source changes only).
4. Open a pull request to `main`.

Once live, update this LGU's entry in the [BetterLGU directory](https://directory.bettergov.ph/) from 🔵 Planned to 🟢 Active.
