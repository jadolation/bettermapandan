---
name: bettermapandan-workflow
description: Edit, build, preview, and validate the Better Mapandan static site efficiently. Use only inside the bettermapandan repository for its pages, datasets, translations, GIS, or build pipeline; never apply to another project.
---

# Better Mapandan workflow

## Repository boundary

This is a repository-local skill, not a global workflow. Before using its
commands or conventions:

1. Run `git rev-parse --show-toplevel` from the task's working directory.
2. Confirm that root is the repository containing this skill at
   `.agents/skills/bettermapandan-workflow/SKILL.md`. Resolve paths before
   comparing them; another checkout of this repository can use its own copy.
3. Confirm `package.json` has name `bettermapandan` and repository URL
   `git+https://github.com/jadolation/bettermapandan.git`, and that
   `_build/orchestrator.py`, `src/pages/`, and `locales/` exist there.

If these checks fail, stop applying this skill. Do not install it in a user-wide
skills folder or apply it to a sibling project. Run subsequent commands from the
confirmed root.

## Find the source once

Read [README.md](../../../README.md) for general context and
[docs/gis.md](../../../docs/gis.md) for GIS tasks. Prefer the current
implementation and `.github/workflows/quality.yml` when older documentation
disagrees. Use this map instead of scanning the entire repository:

| Change | Start here | Connected surfaces |
| --- | --- | --- |
| Page content/layout | `src/pages/`, `src/partials/`, `src/templates/` | Front matter; `src/data/page-meta.json` for localized metadata |
| Services, legislative, transparency data | `src/data/*.json`, `_build/generators/` | `src/data/schemas.py`; matching generator/data tests |
| Shared headline figures | `src/data/municipal-facts.json`, `_build/facts.py` | Existing `{POP_2024}`, `{LAND_AREA}`, `{DENSITY}` placeholders |
| UI text | `locales/en.json`, `fil.json`, `pag.json` | `_build/labels.py`, page metadata; `src/data/pag-review.json` for review status |
| Styling | `assets/css/` | `assets/style.css` import order; `tokens.css` for design values |
| Browser behavior | `assets/*.js`, `assets/js/` | `_build/assets.py:JS_SOURCES`; page script references |
| GIS | `src/pages/gis.html`, `assets/gis-map.js`, `assets/css/map.css` | `src/data/gis/layers.json`, configured sources, `_build/gis*.py`, GIS tests |
| Entity links | `_build/entities.py`, `_build/entity_resolution.py` | `src/data/link_*.py`, entities/relationships, review decisions, generated bundles |
| Build/publication | `build.py`, `_build/orchestrator.py` | `pages.py`, `chrome.py`, `navigation.py`, `preview.py`, `staging.py`, `gis_sync.py` |

Search callers before changing shared helpers. Imports re-exported from
`_build/orchestrator.py` support tests and other scripts. Reuse
`src/data/_utils.py` for extraction/normalization and the existing generators
rather than adding another pipeline.

## Build and preview

Use Python 3.11+; CI also uses Node 22. First-time setup:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Build after the related edits, then serve the artifact:

```sh
python build.py --isolated --offline
python -m http.server 8000 --bind 127.0.0.1 --directory _site
```

Open `http://127.0.0.1:8000/`; GIS is `/gis/`, with mirrors under `/fil/` and
`/pag/`. Rebuild after source changes; the server does not watch or compile.
VS Code Live Server already targets `_site/` on port 5501.

The isolated build uses a disposable workspace and exports only the allowlisted
`_site/` artifact. A plain `python build.py` rewrites checkout output,
deletes/recreates `fil/` and `pag/`, and regenerates data bundles. Prefer isolated
builds for previews. Add `--sync-gis` only when the task needs the checkout's
root GIS mirror refreshed; ordinary isolated builds leave it untouched.

`--offline` avoids build-tool downloads; without an absolute existing
`GIS_ESBUILD_BINARY`, JavaScript is copied to `.min.js` sidecars. Browser CDN
libraries, tiles, and remote services still need connectivity. Do not combine
`--isolated` with `--compress` or `--verify-translations`.

## Check the affected behavior

Choose relevant existing checks; documentation-only edits need no full
application suite. Install test tools into the virtual environment when needed:
`python -m pip install pytest ruff`.

- Python logic/data: `python -m pytest tests/test_<affected_area>.py -q`.
- Locale changes: `python check_i18n.py`; also `python check_pag_coverage.py`
  when touching Pangasinan. The build falls back to English for missing
  Pangasinan strings and does not enforce key parity itself.
- GIS browser logic: `node --test tests/gis-runtime.cjs` needs no npm install.
- Cross-cutting build/data changes: `python -B -m pytest -p no:cacheprovider tests/ -q`,
  `python -m ruff check .`, and `python build.py --isolated --offline`.
- Relevant browser regressions: install locked dependencies with `npm ci`,
  set `CHROME_PATH` to installed Chrome if autodetection fails, then run
  `node tests/browser/gis-explorer.cjs --fixtures` and
  `node tests/browser/gis-explorer.cjs --root "$PWD/_site"` against a fresh build.

`npm test` is a failing placeholder, not the test suite. The GIS browser suite
mocks Leaflet; distinguish those checks from real CDN/map visuals and manual
device checks. Inspect schema warnings: validation failures do not necessarily
make the build exit unsuccessfully. Finish with `git diff --check` and
`git status --short` to catch unintended regenerated files.

## Preserve data and publication boundaries

Edit sources, not `_site/`, minified sidecars, generated locale HTML, or generated
entity bundles. Rebuild derivatives after changing inputs. Raw research lives in
`datasets/`; public downloads and GIS derivatives follow existing staging rules.
Serve and publish `_site/`, never the repository root.

For GIS, keep longitude/latitude order, stable canonical IDs, provenance, and
precision labels. Records without supplied valid coordinates remain nonspatial;
do not invent locations or treat indicative boundaries/historical hazards as
surveyed or current safety information. Use the single configured layer workflow,
not removed `GIS_MODE`/`GIS_RESEARCH_*` settings. Preserve existing no-JavaScript
directories and accessible controls.
