# Better Mapandan

An independent transparency portal for the Municipality of Mapandan, Pangasinan,
built under the [BetterGov.ph](https://bettergov.ph/) BetterLGU initiative.

Dual-language: English at root, Filipino under `/fil/`.

**Live at:** [bettermapandan.org](https://bettermapandan.org) — deployed via GitHub Pages with a Hostinger-registered domain.


## Structure

```
build.py                 Assembles src/pages/*.html + src/partials/*.html
                          into the final static pages below.
                          Flags:
                            (none)           Build all pages (EN + FIL)
                            --compress       Optimize images only (does not build)
                            --verify-translations  Lint untranslated strings only (does not build)

src/
  partials/
    base.html             <head> + <body> shell, with {{TITLE}}, {{DESCRIPTION}},
                           {{HEADER}}, {{BODY}}, {{FOOTER}}, {{LANG_ATTR}},
                           {{CANONICAL_URL}}, {{ASSET_BASE}} placeholders
    header.html            Emergency bar + site nav (single source of truth)
    footer.html            Site footer, incl. {{REPO_URL}}
  pages/
    index.html              Front matter (title/description) + body content only
    about.html              About the municipality
    government.html
    search.html
    statistics.html
    support.html
    support/                Sub-pages: accessibility, faq, privacy, report, sitemap, terms
                            Note: services.html, legislative.html, and transparency.html
                            are generated programmatically by build.py, not sourced here.

locales/
  en.json                English locale strings (UI labels, page copy)
  fil.json               Filipino locale strings

assets/
  style.css              Component-based design tokens and styles — inline styles
                           are limited to data-driven elements (charts, dynamic layouts).
  script.js               Mobile nav toggle, language switcher, weather widget,
                           history carousel, barangay modals, accordions,
                           feedback widget, Lucide icon init.
  logo.svg                Municipal seal — source for the header/footer marks
                           and every generated favicon. DO NOT convert to WebP;
                           the SVG uses mask+filter rendering pipelines.
  municipal-seal.svg      Decorative hero watermark. DO NOT convert to WebP;
                           the SVG uses embedded PNG with SVG filter pipeline.
  Pandan.webp             Hero image (Pandan Festival)
  plaza.webp              Hero image (Town Plaza)
  luyan.webp              Hero image (Luyan)
  favicon.ico, favicon-32x32.png   Generated from logo.svg.
                           Also: android-chrome-*.svg, apple-touch-icon.svg.
  chart-loader.js         Lazy-loads Chart.js only on pages with <canvas>
  barangay-data.js        Barangay population/household data
  search.js, search-index.json   Client-side search

fil/                     Filipino build output — mirrors root structure
  assets/                Copied from assets/ at build time

optimize-images.mjs     Standalone Node.js image optimization (alternative to --compress)

index.html, services.html, government.html,        <- BUILD OUTPUT.
legislative.html, transparency.html                    Don't hand-edit these;
fil/*.html                                                 edit src/ and rebuild.
README.md
```


## Editing content

1. Edit the relevant file in `src/pages/` (page copy, tables, cards — this is
   almost always where you want to be) or `src/partials/` (nav links, footer
   links, `<head>` boilerplate shared by every page).
2. For UI strings (labels, headings, emergency numbers), edit `locales/en.json`
   and/or `locales/fil.json`.
3. Regenerate the site:

   ```bash
   python3 build.py
   ```

   This overwrites `index.html`, `services.html`, `government.html`,
   `legislative.html`, and `transparency.html` at the project root, plus
   their Filipino counterparts under `fil/`. No other tooling required — just
   Python 3, already on every dev machine and CI runner.
4. Commit both the `src/` change and the regenerated root `.html` files —
   the root files are what actually gets served, so they need to be
   committed and up to date (this is a static-file build, not a build-on-
   deploy setup).

Page files use minimal front matter:

```
---
title: <the browser tab title>
description: <meta description>
---
<everything between </header> and <footer> — the actual page content>
```

Styling changes go in `assets/style.css`, which is organized by component
(nav, hero, cards, tables, steps, chart bars, footer) with a token block at
the top (`--green-deep`, `--gold`, `--red-flag`, etc.) — change a token once
to re-theme the whole site.


## Image optimization

Run `python3 build.py --compress` to optimize images before building:

- **JPG compression** — citizens-charter photos (mozjpeg, quality 70)
- **PNG compression** — history photos (quality 60, compression level 9)
- **Hero images → WebP** — `luyan.png`, `Pandan.jpg`, `plaza.jpg` converted
  to WebP (quality 80, max-width 1200)
- **History PNGs → WebP** — `assets/history/*.png` converted to WebP

The following are **NOT** compressed and should stay as original SVGs:
- `logo.svg` — uses `<mask>` + `feColorMatrix` filter pipeline that cannot
  be faithfully extracted to a single raster format
- `municipal-seal.svg` — embedded PNG with SVG filter rendering

Alternatively, run `node optimize-images.mjs` for standalone image
optimization (same pipeline, Node.js only).


## Translation linting

Run `python3 build.py --verify-translations` to check i18n parity between
EN and FIL page outputs. The linter compares rendered HTML text and flags
segments present in EN but absent in FIL.

Known false positives (intentionally the same in both languages):
- Historical dates, proper nouns, place names
- Government acronyms (DILG, BLGF, COA, PhilGEPS)
- Currency amounts and numbers


## Code quality

The project uses these tools to maintain code quality:

```bash
ruff check build.py          # Lint — target: 0 errors
radon cc build.py -a -nc     # Cyclomatic complexity — target: < 10 per function
radon mi build.py             # Maintainability index — target: Grade A
```


## CI/CD

Two GitHub Actions workflows run Lighthouse audits:

**CI workflow** (`.github/workflows/lighthouse.yml`) — runs on every push and
pull request to `main`:

1. Sets up Python 3.11 + Node.js 22
2. Builds the site (`python3 build.py`)
3. Starts a local server on port 9001
4. Runs Lighthouse CI against 11 URLs
5. Asserts thresholds: accessibility ≥ 95, SEO = 100, performance ≥ 50

**Production monitor** (`.github/workflows/lighthouse-production.yml`) — runs
weekly (Monday 8:00 UTC) or manually:

1. Runs Lighthouse against the live site (`bettermapandan.org`)
2. Tests 7 key pages for real-world performance
3. Uploads reports to temporary public storage


## Before you deploy

1. **Rename this repository** to `bettermapandan` and set it up on GitHub,
   per the [BetterLGU guide](https://directory.bettergov.ph/guide).
2. **Update `REPO_URL`** in `build.py` (`SITE_CONFIG`) to your actual repo
   URL, then rebuild — this is the one place that value lives, and it flows
   into the footer's "Source Code" link on every page.
3. **Register a domain**: `bettermapandan.org`, then point it at your host.
4. **Verify the data.** Everything on this site was compiled from public
   sources (Wikipedia, the Provincial Government of Pangasinan, the official
   `mapandan.gov.ph` site, and COA) as of August 2026. Before launch,
   cross-check names, numbers, and figures directly against
   `mapandan.gov.ph` and the Municipal Accountant/Budget Office, since local
   officials and budgets change.


## Deploying

The site is deployed via **GitHub Pages** from the `main` branch root folder.
The custom domain `bettermapandan.org` is registered through **Hostinger**
and configured with DNS A records pointing to GitHub Pages.

Any static host works — the root `.html` files plus `assets/` are the
entire deployable site. `src/` and `build.py` don't need to ship to
production; they're only for maintainers.

- **GitHub Pages**: Settings → Pages → deploy from the `main` branch, root
  folder. Custom domain configured via Hostinger DNS.
- **Netlify / Vercel**: connect the repo with no build command and `/` as
  the publish directory (or add `python3 build.py` as the build command if
  you'd rather have the host regenerate pages on every push).


## Once live

Update this LGU's entry in the
[BetterLGU directory](https://directory.bettergov.ph/) from 🔵 Planned to
🟢 Active, per `CONTRIBUTING.md` in that repository.
