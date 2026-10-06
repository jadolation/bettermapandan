"""Page processors: static/generated pages, page-meta, search entries."""
import json
from pathlib import Path

from _build.chrome import assemble_page, build_footer, build_header, build_hero
from _build.config import SECTION_ANCHORS, SECTION_NAV, SRC_DATA
from _build.generators.barangays import (
    build_barangay_comparison_script,
    generate_barangay_councils_table,
)
from _build.generators.dpwh import generate_dpwh
from _build.generators.fdp import generate_fdp, generate_fdp_dashboard
from _build.generators.fdp_analytics import generate_fdp_summary
from _build.generators.procurement import (
    generate_homepage_dpwh_data,
    generate_homepage_procurement_data,
    generate_procurement,
)
from _build.labels import resolve_body_placeholders
from _build.navigation import (
    build_breadcrumb_jsonld,
    build_breadcrumbs,
    build_lang_switcher_urls,
    build_section_nav,
    build_transparency_tabs,
)
from _build.templates import (
    compute_asset_base,
    compute_url,
    fill,
    strip_html,
    to_folder_index,
)

_PAGE_META_CACHE: dict[str, dict] = {}


def build_search_entry(rel: Path, title: str, description: str, body: str, lang_code: str, anchors_key: str = "") -> dict:
    """Build a search index entry from page content."""
    url = compute_url(rel)
    if lang_code != "en":
        url = f"{lang_code}/{url}"
    plain_body = strip_html(body)
    entry: dict[str, object] = {"title": title, "url": url, "description": description, "body": plain_body}
    if anchors_key:
        anchors = SECTION_ANCHORS.get(anchors_key, [])
        section_anchors = []
        for anchor_id, heading in anchors:
            idx = plain_body.lower().find(heading.lower())
            if idx != -1:
                section_anchors.append({"anchor": anchor_id, "pos": idx})
        section_anchors.sort(key=lambda s: s["pos"])  # type: ignore[arg-type, return-value]
        if section_anchors:
            entry["section_anchors"] = section_anchors
    return entry

def _load_page_meta() -> dict:
    """Localized front-matter overrides (title/description/hero) per page.

    Cached per SRC_DATA so staged test builds pick up the staged file.
    """
    key = str(SRC_DATA)
    if key not in _PAGE_META_CACHE:
        path = SRC_DATA / "page-meta.json"
        data: dict = {}
        if path.exists():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                data = loaded if isinstance(loaded, dict) else {}
            except (json.JSONDecodeError, OSError):
                data = {}
        _PAGE_META_CACHE[key] = data
    return _PAGE_META_CACHE[key]

def _apply_page_meta(meta: dict, rel: Path, lang_code: str) -> dict:
    """Override EN front-matter with fil/pag page metadata when available."""
    if lang_code == "en":
        return meta
    override = _load_page_meta().get(rel.as_posix(), {}).get(lang_code, {})
    if not override:
        return meta
    meta = dict(meta)
    for mkey in ("title", "description", "hero_eyebrow", "hero_lede"):
        if override.get(mkey):
            meta[mkey] = override[mkey]
    return meta

def _process_static_page(
    lang_code: str, locale: dict, rel: Path, meta: dict, body: str,
    base: str, page_hero_raw: str, out_root: Path, search_entries: list
) -> int:
    out_rel = to_folder_index(rel)
    asset_base = compute_asset_base(out_rel, lang_code)
    lang_urls = build_lang_switcher_urls(rel, lang_code)
    meta = _apply_page_meta(meta, rel, lang_code)
    page_title = meta["title"].split(" —")[0].split(" |")[0].strip()
    breadcrumbs = build_breadcrumbs(locale, rel, page_title)
    header = build_header(locale, asset_base, lang_code, lang_urls)
    footer = build_footer(locale, asset_base)
    hero_html = build_hero(meta, page_hero_raw, asset_base)
    body = resolve_body_placeholders(hero_html + body, locale, asset_base)
    if rel.name == "transparency.html" or (len(rel.parts) > 1 and rel.parts[0] == "transparency"):
        proc_html, _, _ = generate_procurement(locale)
        body = body.replace("{PROCUREMENT_SECTION}", proc_html, 1)
        dpwh_html, _, _ = generate_dpwh(locale, asset_base)
        body = body.replace("{DPWH_SECTION}", dpwh_html, 1)
        body = body.replace("{FDP_DASHBOARD}", generate_fdp_dashboard(locale), 1)
        body = body.replace("{FDP_SECTION}", generate_fdp(locale), 1)
    if len(rel.parts) > 1 and rel.parts[0] == "transparency" and rel.stem != "transparency":
        lang_prefix = f"/{lang_code}" if lang_code != "en" else ""
        body = body.replace("{TRANSPARENCY_TABS}", build_transparency_tabs(locale, rel.stem, lang_prefix), 1)
    if rel.name in SECTION_NAV:
        body = body.replace("{SECTION_NAV}", build_section_nav(locale, rel.name, body), 1)
    if rel.name == "index.html":
        proc_data = generate_homepage_procurement_data()
        body = body.replace("{HOMEPAGE_PROCUREMENT_DATA}", proc_data, 1)
        dpwh_data = generate_homepage_dpwh_data()
        body = body.replace("{HOMEPAGE_DPWH_DATA}", dpwh_data, 1)
    if rel.name == "government.html":
        body = body.replace("{BARANGAY_COUNCILS_TABLE}", generate_barangay_councils_table(locale), 1)
    page_url = f"{lang_code}/{rel}" if lang_code != "en" else str(rel)
    breadcrumb_jsonld = build_breadcrumb_jsonld(locale, rel, page_title, lang_code)
    page_html = assemble_page(base, asset_base, meta["title"], meta["description"], header, breadcrumbs + body, footer, lang_code, page_url, breadcrumb_jsonld)

    if rel.name == "statistics.html":
        comparison_script = build_barangay_comparison_script()
        stats_js = '<script defer src="' + asset_base + '/assets/stats.min.js"></script>'
        page_html = page_html.replace("</body>", comparison_script + "\n" + stats_js + "\n</body>", 1)

    if str(rel).replace("\\", "/") == "transparency/projects.html":
        explorer_js = '<script defer src="' + asset_base + '/assets/js/project-explorer.min.js"></script>'
        page_html = page_html.replace("</body>", explorer_js + "</body>", 1)

    # Transparency subpages only (the /transparency/ hub is static — no JS data needed).
    if len(rel.parts) > 1 and rel.parts[0] == "transparency":
        transparency_js = (
            '<script defer src="' + asset_base + '/assets/js/common.min.js"></script>\n'
            '<script defer src="' + asset_base + '/assets/transparency.min.js"></script>\n'
            '<script defer src="' + asset_base + '/assets/js/transparency-charts.min.js"></script>\n'
            '<script defer src="' + asset_base + '/assets/js/procurement-table.min.js"></script>\n'
            '<script defer src="' + asset_base + '/assets/js/fdp-dashboard.min.js"></script>\n'
            '<script defer src="' + asset_base + '/assets/js/dashboard-tabs.min.js"></script>\n'
            '<script defer src="' + asset_base + '/assets/js/section-nav.min.js"></script>\n'
        )
        fdp_summary = generate_fdp_summary()
        transparency_js += '<script>window.FDP_SUMMARY = ' + json.dumps(fdp_summary, ensure_ascii=False) + ';</script>\n'
        csv_data_path = SRC_DATA / "transparency-csv.json"
        if csv_data_path.exists():
            csv_data = json.loads(csv_data_path.read_text(encoding="utf-8"))
            transparency_js += '<script>window.TRANSPARENCY_CSV_DATA = ' + json.dumps(csv_data, ensure_ascii=False) + ';</script>\n'
        audit_data_path = SRC_DATA / "audit-reports.json"
        if audit_data_path.exists():
            audit_data = json.loads(audit_data_path.read_text(encoding="utf-8"))
            transparency_js += '<script>window.AUDIT_DATA = ' + json.dumps(audit_data, ensure_ascii=False) + ';</script>\n'
        page_html = page_html.replace("</body>", transparency_js + "</body>", 1)

    if rel.name == "index.html":
        homepage_js = '<script defer src="' + asset_base + '/assets/stats.min.js"></script>'
        page_html = page_html.replace("</body>", homepage_js + "\n</body>", 1)
    if rel.name == "about.html":
        about_js = '<script defer src="' + asset_base + '/assets/stats.min.js"></script>'
        page_html = page_html.replace("</body>", about_js + "\n</body>", 1)
    if rel.name in SECTION_NAV and "section-nav.min.js" not in page_html:
        section_nav_js = '<script defer src="' + asset_base + '/assets/js/section-nav.min.js"></script>\n'
        page_html = page_html.replace("</body>", section_nav_js + "</body>", 1)

    out_path = out_root / to_folder_index(rel)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page_html, encoding="utf-8")
    print(f"  [{lang_code.upper()}] built {rel}  ({len(page_html):,} bytes)")

    search_entries.append(build_search_entry(rel, meta["title"], meta["description"], body, lang_code, rel.name))
    return 1

def _process_generated_page(
    lang_code: str, locale: dict, rel: Path, body_content: str, page_meta: dict, hero_meta: dict,
    base: str, page_hero_raw: str, out_root: Path, search_entries: list
) -> int:
    out_rel = to_folder_index(rel)
    asset_base = compute_asset_base(out_rel, lang_code)
    lang_urls = build_lang_switcher_urls(rel, lang_code)
    page_title = rel.stem.replace("-", " ").title()
    breadcrumbs = build_breadcrumbs(locale, rel, page_title)
    header = build_header(locale, asset_base, lang_code, lang_urls)
    footer = build_footer(locale, asset_base)

    rel_path_str = str(rel)
    page_hero = hero_meta.get(rel_path_str, {})
    if page_hero:
        hero_html = fill(page_hero_raw, {
            "ASSET_BASE": asset_base,
            "HERO_EYEBROW": page_hero.get("hero_eyebrow", ""),
            "HERO_HEADING": page_hero.get("hero_heading", ""),
            "HERO_LEDE": page_hero.get("hero_lede", ""),
        })
        body_content = hero_html + body_content

    page_url = f"{lang_code}/{rel_path_str}" if lang_code != "en" else rel_path_str
    breadcrumb_jsonld = build_breadcrumb_jsonld(locale, rel, page_title, lang_code)
    if rel.name in SECTION_NAV:
        body_content = body_content.replace("{SECTION_NAV}", build_section_nav(locale, rel.name, body_content), 1)
    page_html = assemble_page(
        base, asset_base,
        page_meta.get(rel_path_str, {}).get("title", "Better Mapandan"),
        page_meta.get(rel_path_str, {}).get("description", ""),
        header, breadcrumbs + body_content, footer, lang_code, page_url, breadcrumb_jsonld
    )
    if rel.name in SECTION_NAV:
        section_nav_js = '<script defer src="' + asset_base + '/assets/js/section-nav.min.js"></script>\n'
        page_html = page_html.replace("</body>", section_nav_js + "</body>", 1)

    out_path = out_root / to_folder_index(rel)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page_html, encoding="utf-8")
    print(f"  [{lang_code.upper()}] built {rel}  ({len(page_html):,} bytes)")

    search_entries.append(build_search_entry(rel, rel.stem.replace("-", " ").title(), "", body_content, lang_code))
    return 1
