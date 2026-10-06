"""Build orchestrator: thin pipeline driver over chrome/navigation/labels/pages."""
import json
import shutil
import sys
from pathlib import Path

from _build.assets import compress_images, generate_llms_txt, generate_sitemap, minify_assets

# Backward-compatible re-exports (tests + external scripts import from here).
from _build.chrome import assemble_page as assemble_page
from _build.chrome import build_footer as build_footer
from _build.chrome import build_header as build_header
from _build.chrome import build_hero as build_hero
from _build.config import (
    FIL_DIR,
    HAS_SCHEMA_VALIDATION,
    LANGUAGES,
    PAG_DIR,
    ROOT,
    SRC_DATA,
    SRC_PAGES,
    SRC_PARTIALS,
    validate_all,
)
from _build.generators.barangays import generate_barangays
from _build.generators.legislative import generate_legislative
from _build.generators.services import generate_services
from _build.labels import _build_homepage_labels as _build_homepage_labels
from _build.labels import _build_page_body_labels as _build_page_body_labels
from _build.labels import _build_search_labels as _build_search_labels
from _build.labels import _build_statistics_labels as _build_statistics_labels
from _build.labels import _build_transparency_labels as _build_transparency_labels
from _build.labels import resolve_body_placeholders as resolve_body_placeholders
from _build.lint import verify_translations
from _build.locales import deep_merge as deep_merge
from _build.locales import load_locale
from _build.navigation import SECTION_NAMES as SECTION_NAMES
from _build.navigation import build_breadcrumb_jsonld as build_breadcrumb_jsonld
from _build.navigation import build_breadcrumbs as build_breadcrumbs
from _build.navigation import build_lang_switcher_urls as build_lang_switcher_urls
from _build.navigation import build_section_nav as build_section_nav
from _build.navigation import build_transparency_tabs as build_transparency_tabs
from _build.pages import _apply_page_meta as _apply_page_meta
from _build.pages import _load_page_meta as _load_page_meta
from _build.pages import _process_generated_page, _process_static_page
from _build.pages import build_search_entry as build_search_entry
from _build.templates import parse_page, strip_front_matter

__all__ = [
    "SECTION_NAMES",
    "_apply_page_meta",
    "_build_homepage_labels",
    "_build_page_body_labels",
    "_build_search_labels",
    "_build_statistics_labels",
    "_build_transparency_labels",
    "_load_page_meta",
    "assemble_page",
    "build",
    "build_breadcrumb_jsonld",
    "build_breadcrumbs",
    "build_footer",
    "build_header",
    "build_hero",
    "build_lang_switcher_urls",
    "build_search_entry",
    "build_section_nav",
    "build_transparency_tabs",
    "deep_merge",
    "main",
    "resolve_body_placeholders",
]


def build() -> None:
    generate_barangays()

    from _build.entities import build_all as build_entities
    entity_summary = build_entities(assets_out=ROOT / "assets")
    print("  entities: {projects} projects, {contracts} contracts, "
          "{contractors} contractors, {funds} funds, {findings} findings, "
          "{bids} bids, {relationships} relationships, {review} review".format(**entity_summary))

    en_locale = load_locale("en")
    fil_locale = load_locale("fil")
    pag_locale_raw = load_locale("pag")
    pag_locale = deep_merge(en_locale, pag_locale_raw)

    if HAS_SCHEMA_VALIDATION:
        schema_errors = validate_all(SRC_DATA)
        if schema_errors:
            print("\nWARNING: Data validation errors found:")
            for err in schema_errors:
                print(f"  - {err}")
            print("")

    base = (SRC_PARTIALS / "base.html").read_text(encoding="utf-8")
    page_hero_raw = (SRC_PARTIALS / "page-hero.html").read_text(encoding="utf-8")

    for out_dir in [FIL_DIR, PAG_DIR]:
        if out_dir.exists():
            shutil.rmtree(out_dir)

    cname_src = ROOT / "CNAME"
    if not cname_src.exists():
        (ROOT / "CNAME").write_text("bettermapandan.org\n", encoding="utf-8")
        print("  CNAME: generated")

    all_search_entries = []

    for lang_code, out_root, _ in LANGUAGES:
        locale = {"en": en_locale, "fil": fil_locale, "pag": pag_locale}[lang_code]
        print(f"\n--- Building [{lang_code.upper()}] ---")

        svc_pages, svc_meta, svc_hero_meta = generate_services(locale, lang_code)
        leg_html, leg_meta, leg_hero_meta = generate_legislative(locale, lang_code)
        svc_pages["legislative.html"] = leg_html
        svc_meta["legislative.html"] = leg_meta
        svc_hero_meta["legislative.html"] = leg_hero_meta

        page_files = sorted(SRC_PAGES.rglob("*.html"))
        if not page_files:
            raise SystemExit(f"No page sources found in {SRC_PAGES}")

        search_entries: list[dict] = []
        count = 0

        for page_path in page_files:
            rel = page_path.relative_to(SRC_PAGES)
            meta, body = parse_page(page_path.read_text(encoding="utf-8"))
            count += _process_static_page(
                lang_code, locale, rel, meta, body, base, page_hero_raw, out_root, search_entries
            )

        for rel_path, body_content in svc_pages.items():
            body_content = strip_front_matter(body_content)
            rel = Path(rel_path)
            count += _process_generated_page(
                lang_code, locale, rel, body_content, svc_meta, svc_hero_meta, base, page_hero_raw, out_root, search_entries
            )

        all_search_entries.extend(search_entries)
        print(f"  [{lang_code.upper()}] search index: {len(search_entries)} entries")

    (ROOT / "assets" / "search-index.json").write_text(
        json.dumps(all_search_entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nSearch index: {len(all_search_entries)} total entries")

    minify_assets()

    assets_src = ROOT / "assets"
    for out_dir in [FIL_DIR, PAG_DIR]:
        assets_dst = out_dir / "assets"
        if assets_src.exists():
            if assets_dst.exists():
                shutil.rmtree(assets_dst)
            shutil.copytree(assets_src, assets_dst)
            print(f"\n  Copied assets to {out_dir.name}/assets/")

    generate_sitemap()
    generate_llms_txt()
    print(f"\nDone. {count * len(LANGUAGES)} page(s) written ({count} per language)")


def main():
    if "--compress" in sys.argv:
        compress_images()
    if "--verify-translations" in sys.argv:
        verify_translations()
    if "--compress" not in sys.argv and "--verify-translations" not in sys.argv:
        build()
