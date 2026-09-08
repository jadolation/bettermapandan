# Better Mapandan

An independent transparency portal for the Municipality of Mapandan, Pangasinan,
built under the [BetterGov.ph](https://bettergov.ph/) BetterLGU initiative.


## Structure

```
build.py                 Assembles src/pages/*.html + src/partials/*.html
                          into the final static pages below.

src/
  partials/
    base.html             <head> + <body> shell, with {{TITLE}}, {{DESCRIPTION}},
                           {{HEADER}}, {{BODY}}, {{FOOTER}} placeholders
    header.html            Emergency bar + site nav (single source of truth)
    footer.html            Site footer, incl. {{REPO_URL}}
  pages/
    index.html              Front matter (title/description) + body content only
    services.html           for each page — no repeated header/footer here.
    government.html
    legislative.html
    transparency.html

assets/
  style.css              All design tokens and styles — zero inline styles
                          anywhere in the generated HTML.
  script.js               Mobile nav toggle (the only JS on the site).
  logo.svg                Municipal seal — source for the header/footer marks
                           and every generated favicon.
  favicon.ico, favicon-*.png   Generated from logo.svg.

index.html, services.html, government.html,        <- BUILD OUTPUT.
legislative.html, transparency.html                    Don't hand-edit these;
                                                        edit src/ and rebuild.
README.md
```

## Editing content

1. Edit the relevant file in `src/pages/` (page copy, tables, cards — this is
   almost always where you want to be) or `src/partials/` (nav links, footer
   links, `<head>` boilerplate shared by every page).
2. Regenerate the site:

   ```bash
   python3 build.py
   ```

   This overwrites `index.html`, `services.html`, `government.html`,
   `legislative.html`, and `transparency.html` at the project root. No other
   tooling required — just Python 3, already on every dev machine and CI
   runner.
3. Commit both the `src/` change and the regenerated root `.html` files —
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

Any static host works — the root `.html` files plus `assets/` are the
entire deployable site. `src/` and `build.py` don't need to ship to
production; they're only for maintainers.

- **GitHub Pages** (simplest): Settings → Pages → deploy from the `main`
  branch, root folder.
- **Netlify / Vercel**: connect the repo with no build command and `/` as
  the publish directory (or add `python3 build.py` as the build command if
  you'd rather have the host regenerate pages on every push).

## Once live

Update this LGU's entry in the
[BetterLGU directory](https://directory.bettergov.ph/) from 🔵 Planned to
🟢 Active, per `CONTRIBUTING.md` in that repository.
