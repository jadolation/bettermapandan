# Better Mapandan repository overview

Better Mapandan is an independent public-information and transparency portal for
Mapandan, Pangasinan, under the BetterLGU initiative. It brings together municipal
services, government and barangay information, statistics, procurement, DPWH
projects, budgets and FDP disclosures, COA audit findings, and an interactive GIS
explorer. Entity relationships connect projects, contracts, contractors, funds,
and audit findings for cross-referencing.

## Architecture and source map

This is a Python-generated static website with HTML templates, modular CSS, and
plain browser JavaScript. It has no application server or database to start.
English pages live at `/`, Filipino at `/fil/`, and Pangasinan at `/pag/`.
Browser features include client-side search, charts, filters, and Leaflet maps.

| Path | Purpose |
| --- | --- |
| `build.py`, `_build/` | Build entry point, page assembly, translations, generators, entity linking, asset processing, GIS, and publication staging |
| `src/pages/` | Editable page HTML with metadata front matter |
| `src/partials/`, `src/templates/` | Shared shell, navigation, footer, cards, and generated-page templates |
| `src/data/` | Structured content, municipal facts, schemas, extraction/linking helpers, entities, and relationships |
| `locales/` | English, Filipino, and Pangasinan strings |
| `assets/` | CSS partials, browser scripts, images, fonts, and data bundles |
| `src/data/gis/`, `datasets/GIS/` | Layer configuration, features, provenance, and GIS inputs |
| `datasets/` | Raw research documents, audit reports, disclosure workbooks, and extraction/review inputs |
| `tests/` | Python data/build regressions, Node GIS runtime tests, and Chrome browser checks |
| `.github/workflows/` | Quality checks, Lighthouse audits, and GitHub Pages deployment |
| `docs/gis.md` | Detailed GIS editing, build, preview, and synchronization workflow |
| `.agents/skills/bettermapandan-workflow/` | Repository-local agent workflow skill |

The build reads content and locales, generates service and transparency sections
and entity relationships, assembles the three language trees, processes assets,
and generates the search index and sitemap. The recommended isolated build runs
in a disposable workspace, then exports the publishable website to `_site/`.
GitHub Pages deploys that tested artifact through `.github/workflows/pages.yml`.

## Run locally

Use **Python 3.11+**. From the repository root, create a virtual environment and
install the Python dependencies (`jsonschema`, `openpyxl`, and Pillow):

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python build.py --isolated --offline
python -m http.server 8000 --bind 127.0.0.1 --directory _site
```

Open <http://127.0.0.1:8000/>. The GIS explorer is at
<http://127.0.0.1:8000/gis/>; language mirrors are under `/fil/` and `/pag/`.
Stop the server with Ctrl+C. On later sessions, activate `.venv`, rebuild after
editing sources, and restart the server as needed. There is no hot-reload command.
VS Code Live Server is also configured to serve `_site/` on port 5501.

Node/npm packages are unnecessary for this offline preview build. **Node 22+**
is useful for the Node test suite; run `npm ci` for Lighthouse and Puppeteer
browser tooling. `package.json` does not define `npm run dev` or a working
`npm test` command.

`--offline` avoids downloading build tools, but the browser can still need the
internet for CDN libraries, map tiles, and remote services. JavaScript uses
copy-through `.min.js` files unless `GIS_ESBUILD_BINARY` points to an existing
absolute local executable.

## Common development checks

Install development tools only when needed:

```sh
python -m pip install pytest ruff
python -m pytest tests/ -q
node --test tests/gis-runtime.cjs
python check_i18n.py
python check_pag_coverage.py
python -m ruff check .
git diff --check
```

Run the affected Python test files for smaller changes. The current CI workflow
also checks code complexity, builds `_site/`, runs GIS browser regressions, and
checks internal links before deployment. GIS browser checks use a controlled
Leaflet mock; real map rendering and device behavior need separate verification.

## Editing and workflow notes

- Edit `src/`, `locales/`, and source assets. Generated HTML, minified files, and
  `_site/` are build outputs. Use `src/data/municipal-facts.json` for shared
  population/area figures rather than duplicating values across pages.
- Keep all three locales aligned. Pangasinan has an English fallback and a
  separate speaker-review list; build success alone does not establish parity.
- Prefer `python build.py --isolated --offline`. Plain `python build.py` is the
  legacy checkout build and replaces generated locale trees. Add `--sync-gis`
  to the isolated command only when you need to refresh root GIS mirrors.
- Serve and publish only `_site/`. Research inputs and review material belong
  outside the public artifact; `_build/staging.py` defines publication rules.
- GIS layers come from `src/data/gis/layers.json`. Preserve source provenance,
  coordinate precision, and nonspatial records. See [the GIS guide](gis.md)
  before changing boundaries, overlays, or publication behavior.

## Internal workflow skill

The [Better Mapandan workflow skill](../.agents/skills/bettermapandan-workflow/SKILL.md)
maps tasks to source files and existing checks, and describes safe local builds,
translation handling, GIS conventions, and artifact boundaries. Invoke it as
`$bettermapandan-workflow` while working in this repository, or let Codex select
it for matching tasks.

It lives in this repository's `.agents/skills/`, with no global installation.
That is the [repository-scoped skill discovery location](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills).
Its instructions also require checking the active repository's root and identity
before applying the workflow, and stopping if they do not match.
