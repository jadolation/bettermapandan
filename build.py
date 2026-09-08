#!/usr/bin/env python3
"""
build.py — assembles the Better Mapandan static site.

Supports dual-language output (EN at root, FIL under /fil/).
Locale strings loaded from locales/en.json and locales/fil.json.

Run:
    python3 build.py                  Build all pages (EN + FIL)
    python3 build.py --compress       Compress images, then build
    python3 build.py --verify-translations  Lint untranslated strings

Output: all pages written to the project root (EN) and /fil/ (FIL).

Table of Contents:
    Section 1: Imports & constants              (lines 14-70)
    Section 2: Locale helpers                   (lines 72-105)
    Section 3: Template utilities               (lines 107-165)
    Section 4: Service generator                (lines 167-407)
    Section 5: Legislative generator            (lines 409-616)
    Section 6: Barangay data generator          (lines 618-683)
    Section 7: Translation linter               (lines 685-783)
    Section 8: Image compression                (lines 785-917)
    Section 9: Build helpers (refactored)      (lines 919-1200)
    Section 10: Main build orchestrator         (lines 1202-1350)
"""

import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC_PAGES = ROOT / "src" / "pages"
SRC_PARTIALS = ROOT / "src" / "partials"
SRC_DATA = ROOT / "src" / "data"
SRC_TEMPLATES = ROOT / "src" / "templates"
LOCALES_DIR = ROOT / "locales"
FIL_DIR = ROOT / "fil"

SITE_CONFIG = {
    "REPO_URL": "https://github.com/jadolation/bettermapandan.git",
}

SECTION_ANCHORS = {
    "government.html": [
        ("executive", "Executive Branch"),
        ("legislative", "Legislative Branch"),
        ("barangay-councils", "Barangay Councils"),
        ("departments", "Departments"),
        ("contacts", "Contact Directory"),
    ],
    "legislative.html": [
        ("governance-framework", "Local governance"),
        ("ordinances", "Municipal ordinances"),
        ("resolutions", "Resolutions"),
        ("executive-issuances", "Executive issuances"),
        ("fiscal", "Budgets"),
        ("trends", "Legislative trends"),
    ],
    "statistics.html": [
        ("population", "Demographic overview"),
        ("economy", "Economic indicators"),
        ("fiscal-data", "Revenue"),
    ],
    "transparency.html": [
        ("appropriations", "Current budget"),
        ("revenue", "Revenue"),
        ("fiscal-snapshot", "Fiscal snapshot"),
        ("compliance", "Audit"),
    ],
}

FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)

LANGUAGES = [
    ("en", ROOT, False),
    ("fil", FIL_DIR, True),
]


# ---------------------------------------------------------------------------
# Locale helpers
# ---------------------------------------------------------------------------

def load_locale(lang: str) -> dict:
    """Load a locale JSON file. Returns empty dict if missing."""
    path = LOCALES_DIR / f"{lang}.json"
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"WARNING: Malformed JSON in {path}: {e}")
        return {}


def t(locale: dict, key: str, default: str = "") -> str:
    """Dot-notation locale lookup with fallback to default."""
    parts = key.split(".")
    val: object = locale
    for p in parts:
        if isinstance(val, dict) and p in val:
            val = val[p]
        else:
            return default
    return str(val) if val else default


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------

def parse_page(text: str) -> tuple[dict, str]:
    match = FRONT_MATTER_RE.match(text)
    if not match:
        raise SystemExit("Page is missing --- front matter (title/description).")
    meta_block, body = match.groups()
    meta = {}
    for line in meta_block.splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    for required in ("title", "description"):
        if required not in meta:
            raise SystemExit(f"Page is missing required front matter field: {required}")
    return meta, body.strip("\n")


def fill(template: str, values: dict) -> str:
    for key, value in values.items():
        str_value = str(value) if value is not None else ""
        template = template.replace("{{" + key + "}}", str_value)
        template = template.replace("{" + key + "}", str_value)
    return template


def strip_html(html_text: str) -> str:
    from html.parser import HTMLParser
    class TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.result = []
        def handle_data(self, data):
            self.result.append(data)
        def get_text(self):
            return " ".join(self.result)
    parser = TextExtractor()
    try:
        parser.feed(html_text)
        text = parser.get_text()
    except Exception as _:  # noqa: BLE001 - intentional fallback to regex on any parse error
        text = re.sub(r"<[^>]+>", " ", html_text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def strip_front_matter(text: str) -> str:
    """Remove YAML front matter (--- ... ---) from the start of a template."""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3:].lstrip("\n")
    return text


def compute_url(rel_path: Path) -> str:
    return "/".join(rel_path.parts)


# ---------------------------------------------------------------------------
# Service generation (locale-aware)
# ---------------------------------------------------------------------------

def generate_services(locale: dict, lang: str, is_fil: bool) -> tuple[dict[str, str], dict[str, dict], dict[str, dict]]:
    """Generate service detail pages and directory page.
    Returns (pages, metadata, hero_metadata) where pages is {relative_path: html_content}
    and metadata is {relative_path: {title, description}} for SEO."""
    data_path = SRC_DATA / "services.json"
    try:
        svc_template = (SRC_TEMPLATES / "service.html").read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(f"ERROR: Template file not found: {SRC_TEMPLATES / 'service.html'}")
    try:
        dir_template = (SRC_TEMPLATES / "services-directory.html").read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(f"ERROR: Template file not found: {SRC_TEMPLATES / 'services-directory.html'}")

    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"ERROR: Malformed JSON in {data_path}: {e}")

    services = data.get("services", [])
    try:
        categories = {c["slug"]: c for c in data.get("categories", [])}
    except KeyError as e:
        raise SystemExit(f"ERROR: Category missing 'slug' field in {data_path}: {e}")

    by_category: dict[str, list[dict]] = {}
    for svc in services:
        by_category.setdefault(svc.get("category", ""), []).append(svc)

    pages = {}
    meta = {}
    hero_meta_dict = {}

    svc_labels = _build_service_labels(locale)

    for svc in services:
        svc_slug, filled, hero_meta = _generate_single_service(
            svc, categories, services, svc_template, svc_labels, is_fil
        )
        pages[f"services/{svc_slug}.html"] = filled
        meta[f"services/{svc_slug}.html"] = {
            "title": f"{svc.get('name', '')} — BetterMapandan.org",
            "description": svc.get("description", "")[:160],
        }
        hero_meta_dict[f"services/{svc_slug}.html"] = hero_meta

    dir_filled, dir_hero_meta = _generate_services_directory(
        data, by_category, dir_template, svc_labels, is_fil, asset_base="."
    )
    pages["services.html"] = dir_filled
    meta["services.html"] = {
        "title": t(locale, "services_dir.title", "Services") + " — BetterMapandan.org",
        "description": t(locale, "services_dir.desc", "Find the service you need."),
    }
    hero_meta_dict["services.html"] = dir_hero_meta
    return pages, meta, hero_meta_dict


def _build_service_labels(locale: dict) -> dict:
    return {
        "SVC_DESCRIPTION_LABEL": t(locale, "service_page.description", "Description"),
        "SVC_REQUIREMENTS_LABEL": t(locale, "service_page.requirements", "Requirements"),
        "SVC_PROCEDURE_LABEL": t(locale, "service_page.procedure", "Procedure"),
        "SVC_DETAILS_LABEL": t(locale, "service_page.details", "Service Details"),
        "SVC_OFFICE_LABEL": t(locale, "service_page.office", "Responsible Office:"),
        "SVC_CLASSIFICATION_LABEL": t(locale, "service_page.classification", "Classification:"),
        "SVC_MODE_LABEL": t(locale, "service_page.mode", "Mode:"),
        "SVC_PROCESSING_TIME_LABEL": t(locale, "service_page.processing_time", "Processing Time:"),
        "SVC_FEE_LABEL": t(locale, "service_page.fee", "Fee:"),
        "SVC_WHERE_LABEL": t(locale, "service_page.where_to_apply", "Where to Apply:"),
        "SVC_CONTACT_LABEL": t(locale, "service_page.contact", "Contact:"),
        "SVC_SOURCE_LABEL": t(locale, "service_page.source", "Source:"),
        "SVC_LAST_UPDATED_LABEL": t(locale, "service_page.last_updated", "Last Updated:"),
        "SVC_SCANNED_DOC_LABEL": t(locale, "service_page.scanned_doc", "Scanned Document"),
        "SVC_SCANNED_DOC_DESC": t(locale, "service_page.scanned_doc_desc", ""),
        "SVC_RELATED_LABEL": t(locale, "service_page.related", "Related Services"),
        "SVC_NO_RELATED": t(locale, "service_page.no_related", "No related services available."),
        "SVC_WAS_HELPFUL": t(locale, "service_page.was_helpful", "Was this information helpful?"),
        "SVC_YES": t(locale, "service_page.yes", "Yes"),
        "SVC_NO": t(locale, "service_page.no", "No"),
        "SVC_THANKS": t(locale, "service_page.thanks", "Thank you for your feedback!"),
        "SVC_REPORT": t(locale, "service_page.report", "Report incorrect information"),
    }


def _generate_single_service(svc: dict, categories: dict, services: list, template: str, labels: dict, is_fil: bool):
    cat = categories.get(svc.get("category", ""), {})
    svc_name = svc.get("name_fil", svc.get("name", "")) if is_fil else svc.get("name", "")
    svc_desc = svc.get("description_fil", svc.get("description", "")) if is_fil else svc.get("description", "")
    cat_name = cat.get("name_fil", cat.get("name", "")) if is_fil else cat.get("name", "")
    hero_lede = svc.get("hero_lede_fil", svc.get("hero_lede", svc_desc)) if is_fil else svc.get("hero_lede", svc.get("description", ""))

    reqs_html = "\n".join(f"            <li>{html.escape(r)}</li>" for r in svc.get("requirements", []))
    proc_html = "\n".join(f"            <li>{html.escape(p)}</li>" for p in svc.get("procedure", []))
    related_html = _build_related_links(svc, services, is_fil)
    photo_html = _build_photo_html(svc, is_fil)

    filled = fill(template, {
        "NAME": html.escape(svc_name),
        "DESCRIPTION": html.escape(svc_desc),
        "CATEGORY_NAME": html.escape(cat_name),
        "HERO_LEDE": html.escape(hero_lede),
        "DESCRIPTION_FULL": html.escape(svc.get("description_full", svc.get("description", ""))),
        "REQUIREMENTS": reqs_html,
        "PROCEDURE": proc_html,
        "OFFICE": html.escape(svc.get("office", "")),
        "CLASSIFICATION": html.escape(svc.get("classification", "")),
        "PROCESSING_TIME": html.escape(svc.get("processing_time", "")),
        "FEE": html.escape(svc.get("fee", "Free")),
        "WHERE": html.escape(svc.get("where_to_apply", "")),
        "CONTACT": html.escape(svc.get("contact", "")),
        "SOURCE": html.escape(svc.get("source", "Mapandan Citizen's Charter")),
        "LAST_UPDATED": html.escape(svc.get("last_updated", "August 2025")),
        "RELATED_SERVICES": related_html,
        "PHOTO_HTML": photo_html,
        "DELIVERY_MODE": html.escape(svc.get("delivery_mode", "in-person")),
        "SLUG": html.escape(svc.get("slug", "")),
        **labels,
    })

    svc_slug = svc.get("slug", "unknown")
    hero_meta = _extract_hero_meta(filled)
    return svc_slug, filled, hero_meta


def _build_related_links(svc: dict, services: list, is_fil: bool) -> str:
    related = svc.get("related", [])
    if not related:
        return '<p>No related services available.</p>'
    links = []
    for rel_slug in related:
        rel_svc = next((s for s in services if s.get("slug") == rel_slug), None)
        if rel_svc:
            rel_name = rel_svc.get("name_fil", rel_svc.get("name", "Unknown Service")) if is_fil else rel_svc.get("name", "Unknown Service")
            links.append(f'<a href="{html.escape(rel_slug)}.html">{html.escape(rel_name)}</a>')
    return '<div class="service-links">\n' + "\n".join(f"          {link}" for link in links) + "\n        </div>"


def _build_photo_html(svc: dict, is_fil: bool) -> str:
    photo_ref = svc.get("photo-referenced", "")
    if not photo_ref:
        return ""
    photo_filename = photo_ref.split("/")[-1]
    img_prefix = "../" if not is_fil else "../../"
    service_name = html.escape(svc.get("name", ""))
    return f'''
            <figure class="service-photo-container">
                <img class="service-photo" src="{img_prefix}{photo_ref}" alt="Citizens Charter for {service_name}"
                    loading="lazy"
                    data-fallback="hide">
                <figcaption class="service-photo-caption">
                    Citizens Charter document: {html.escape(photo_filename)}
                </figcaption>
            </figure>'''


def _generate_services_directory(data: dict, by_category: dict, template: str, labels: dict, is_fil: bool, asset_base: str = "."):
    category_cards = []
    for cat in data.get("categories", []):
        cat_services = by_category.get(cat.get("slug", ""), [])
        cat_name = cat.get("name_fil", cat.get("name", "")) if is_fil else cat.get("name", "")
        cat_desc = cat.get("description_fil", cat.get("description", "")) if is_fil else cat.get("description", "")
        service_links = _build_category_service_links(cat_services, is_fil)
        card = (
            f'      <div class="card service-category-card">\n'
            f'        <div class="service-card-head">\n'
            f'          <div class="service-icon"><i data-lucide="{html.escape(cat.get("icon", ""))}"></i></div>\n'
            f'          <h3>{html.escape(cat_name)}</h3>\n'
            f'        </div>\n'
            f'        <p>{html.escape(cat_desc)}</p>\n'
            f'        <div class="service-links">\n'
            + "\n".join(f"          {link}" for link in service_links)
            + "\n        </div>\n"
            '      </div>'
        )
        category_cards.append(card)

    dir_filled = fill(template, {
        "ASSET_BASE": asset_base,
        "CATEGORY_CARDS": "\n".join(category_cards),
        "SVC_TITLE": t(labels, "services_dir.title", "Services"),
        "SVC_EYEBROW": t(labels, "services_dir.eyebrow", "Citizen's Charter"),
        "SVC_LEDE": t(labels, "services_dir.lede", "Every service Mapandan offers."),
        "SVC_DESC": t(labels, "services_dir.desc", "Find the service you need."),
        "SVC_SEARCH_PLACEHOLDER": t(labels, "services_dir.search_placeholder", "Search services..."),
        "SVC_NO_RESULTS": t(labels, "services_dir.no_results", "No services match your search."),
        "SVC_BROWSE_ALL": t(labels, "services_dir.browse_all", "browse all categories"),
        "SVC_NATIONAL_EYEBROW": t(labels, "services_dir.national_eyebrow", "National Platforms"),
        "SVC_NATIONAL_TITLE": t(labels, "services_dir.national_title", "Online services"),
        "SVC_NATIONAL_DESC": t(labels, "services_dir.national_desc", "Several national government services are available online."),
        "SVC_PHILSYS": t(labels, "services_dir.national_philsys", "PhilSys National ID"),
        "SVC_PHILSYS_DESC": t(labels, "services_dir.national_philsys_desc", ""),
        "SVC_PSA": t(labels, "services_dir.national_psa", "PSA Serbilis"),
        "SVC_PSA_DESC": t(labels, "services_dir.national_psa_desc", ""),
        "SVC_EGOV": t(labels, "services_dir.national_egov", "eGovPH"),
        "SVC_EGOV_DESC": t(labels, "services_dir.national_egov_desc", ""),
        "SVC_ELGU": t(labels, "services_dir.national_elgu", "e-LGU Portal"),
        "SVC_ELGU_DESC": t(labels, "services_dir.national_elgu_desc", ""),
    })
    hero_meta = _extract_hero_meta(dir_filled)
    return dir_filled, hero_meta


def _build_category_service_links(cat_services: list, is_fil: bool) -> list:
    service_links = []
    for s in cat_services:
        s_name = s.get("name_fil", s.get("name", "")) if is_fil else s.get("name", "")
        name_html = html.escape(s_name)
        time_html = html.escape(s.get("processing_time", "")) if s.get("processing_time") else ""
        fee_html = html.escape(s.get("fee", "")) if s.get("fee") else ""
        meta_html = _build_service_meta_html(time_html, fee_html)
        service_links.append(
            f'<div class="service-link-wrap">'
            f'<a class="service-link" href="services/{html.escape(s.get("slug", ""))}.html">{name_html}</a>'
            f'{meta_html}</div>'
        )
    return service_links


def _build_service_meta_html(time_html: str, fee_html: str) -> str:
    if not time_html and not fee_html:
        return ""
    parts = []
    if time_html:
        parts.append(f'<span class="service-link-time">{time_html}</span>')
    if fee_html:
        parts.append(f'<span class="service-link-fee">{fee_html}</span>')
    return f'<div class="service-link-meta">{"".join(parts)}</div>'


def _extract_hero_meta(filled: str) -> dict:
    hero_meta = {}
    hero_meta_match = FRONT_MATTER_RE.match(filled)
    if hero_meta_match:
        hero_block = hero_meta_match.group(1)
        for line in hero_block.splitlines():
            key, _, value = line.partition(":")
            key = key.strip()
            if key in ("hero_eyebrow", "hero_heading", "hero_lede"):
                hero_meta[key] = value.strip()
    return hero_meta


# ---------------------------------------------------------------------------
# Legislative generation (locale-aware)
# ---------------------------------------------------------------------------

def generate_legislative(locale: dict, is_fil: bool) -> tuple[str, dict, dict]:
    """Generate legislative page HTML. Returns (html, metadata, hero_meta) for SEO."""
    data_path = SRC_DATA / "legislative.json"
    try:
        template = (SRC_TEMPLATES / "legislative.html").read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(f"ERROR: Template file not found: {SRC_TEMPLATES / 'legislative.html'}")

    match = FRONT_MATTER_RE.match(template)
    if match:
        meta_block, _ = match.groups()
        hero_meta = {}
        for line in meta_block.splitlines():
            key, _, value = line.partition(":")
            key = key.strip()
            if key in ("hero_eyebrow", "hero_heading", "hero_lede"):
                hero_meta[key] = value.strip()
    else:
        hero_meta = {}

    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"ERROR: Malformed JSON in {data_path}: {e}")

    filled = _fill_legislative_template(template, data, locale)
    return filled, {
        "title": t(locale, "legislative.ord_title", "Municipal ordinances") + " — BetterMapandan.org",
        "description": t(locale, "legislative.ord_desc", "Ordinances, resolutions, and executive issuances for the Municipality of Mapandan."),
    }, hero_meta


def _fill_legislative_template(template: str, data: dict, locale: dict) -> str:
    category_labels = data.get("category_labels", {})
    ord_rows = _build_ordinance_rows(data.get("ordinances", []), category_labels)
    res_rows = _build_resolution_rows(data.get("resolutions", []))
    exec_rows = _build_executive_rows(data.get("executive_issuances", []))
    fiscal_cards = _build_fiscal_cards(data.get("fiscal", []))
    trend_cards = _build_trend_cards(data.get("legislative_trends", []))
    process_steps = _build_process_steps(data.get("legislative_process", []))

    gw = data.get("governance_framework", {})

    return fill(template, {
        "HISTORY": gw.get("history", ""),
        "MUNICIPAL_CLASS": gw.get("municipal_class", ""),
        "LAND_AREA": gw.get("land_area", ""),
        "BARANGAYS": str(gw.get("barangays", "")),
        "ORDINANCES_ROWS": "\n          ".join(ord_rows),
        "RESOLUTIONS_ROWS": "\n          ".join(res_rows),
        "EXECUTIVE_ROWS": "\n          ".join(exec_rows),
        "FISCAL_CARDS": "\n      ".join(fiscal_cards),
        "TRENDS_CARDS": "\n      ".join(trend_cards),
        "PROCESS_STEPS": "\n      ".join(process_steps),
        ** _build_legislative_labels(locale),
    })


def _build_legislative_labels(locale: dict) -> dict:
    return {
        "LEG_FRAMEWORK_EYEBROW": t(locale, "legislative.framework_eyebrow", "Framework"),
        "LEG_FRAMEWORK_TITLE": t(locale, "legislative.framework_title", "Local governance & statutory origins"),
        "LEG_LEGAL_BASIS": t(locale, "legislative.legal_basis", "Legal Basis"),
        "LEG_LEGAL_BASIS_DESC": t(locale, "legislative.legal_basis_desc", ""),
        "LEG_HISTORICAL_ORIGINS": t(locale, "legislative.historical_origins", "Historical Origins"),
        "LEG_MUNICIPAL_CLASS": t(locale, "legislative.municipal_class", "Municipal Class"),
        "LEG_LAND_AREA": t(locale, "legislative.land_area", "Land Area"),
        "LEG_BARANGAYS": t(locale, "legislative.barangays_count", "Barangays"),
        "LEG_ORD_EYEBROW": t(locale, "legislative.ord_eyebrow", "Database"),
        "LEG_ORD_TITLE": t(locale, "legislative.ord_title", "Municipal ordinances"),
        "LEG_ORD_DESC": t(locale, "legislative.ord_desc", ""),
        "LEG_ORD_NO": t(locale, "legislative.ord_no", "Ordinance No."),
        "LEG_ORD_TITLE_COL": t(locale, "legislative.ord_title_col", "Title"),
        "LEG_ORD_DATE": t(locale, "legislative.ord_date", "Date"),
        "LEG_ORD_CATEGORY": t(locale, "legislative.ord_category", "Category"),
        "LEG_ORD_SP_REVIEW": t(locale, "legislative.ord_sp_review", "SP Review"),
        "LEG_ORD_STATUS": t(locale, "legislative.ord_status", "Status"),
        "LEG_ORD_SOURCE": t(locale, "legislative.ord_source", "Source"),
        "LEG_RES_EYEBROW": t(locale, "legislative.res_eyebrow", "Resolutions"),
        "LEG_RES_TITLE": t(locale, "legislative.res_title", "Resolutions & investment plans"),
        "LEG_RES_DESC": t(locale, "legislative.res_desc", ""),
        "LEG_RES_NO": t(locale, "legislative.res_no", "Resolution No."),
        "LEG_RES_TITLE_COL": t(locale, "legislative.res_title_col", "Title"),
        "LEG_RES_DATE": t(locale, "legislative.res_date", "Date Approved"),
        "LEG_RES_FISCAL": t(locale, "legislative.res_fiscal", "Fiscal Impact"),
        "LEG_RES_SOURCE": t(locale, "legislative.res_source", "Source"),
        "LEG_EXEC_EYEBROW": t(locale, "legislative.exec_eyebrow", "Executive"),
        "LEG_EXEC_TITLE": t(locale, "legislative.exec_title", "Executive issuances"),
        "LEG_EXEC_DESC": t(locale, "legislative.exec_desc", ""),
        "LEG_EXEC_NAME": t(locale, "legislative.exec_name", "Title"),
        "LEG_EXEC_DATE": t(locale, "legislative.exec_date", "Date"),
        "LEG_EXEC_AUTHORITY": t(locale, "legislative.exec_authority", "Authority"),
        "LEG_EXEC_DESC_COL": t(locale, "legislative.exec_desc_col", "Description"),
        "LEG_BUDGET_TITLE": t(locale, "legislative.budget_title", "Municipal budget"),
        "LEG_BUDGET_DESC": t(locale, "legislative.budget_desc", ""),
        "LEG_TRENDS_TITLE": t(locale, "legislative.trends_title", "Legislative trends"),
        "LEG_TRENDS_DESC": t(locale, "legislative.trends_desc", ""),
    }


def _build_ordinance_rows(ordinances: list, category_labels: dict) -> list:
    rows = []
    for o in ordinances:
        cat_label = category_labels.get(o.get("category", ""), o.get("category", "").title())
        status_class = _get_status_class(o.get("status", ""))
        status_text = o.get("status", "").title()
        source = _build_source_link(o.get("source_url", ""))
        cat_class = html.escape(o.get("category", ""))
        rows.append(
            f'<tr>'
            f'<td>{html.escape(o.get("number", ""))}</td>'
            f'<td>{html.escape(o.get("title", ""))}</td>'
            f'<td>{html.escape(o.get("date_enacted", ""))}</td>'
            f'<td><span class="category-pill category-{cat_class}">{html.escape(cat_label)}</span></td>'
            f'<td>{html.escape(o.get("sp_review", ""))}</td>'
            f'<td><span class="pill {status_class}">{status_text}</span></td>'
            f'<td>{source}</td>'
            f'</tr>'
        )
    return rows


def _build_resolution_rows(resolutions: list) -> list:
    rows = []
    for r in resolutions:
        fiscal = _format_fiscal_value(r.get("fiscal_value"), decimals=2)
        res_source = _build_source_link(r.get("source_url", ""))
        rows.append(
            f'<tr>'
            f'<td>{html.escape(r.get("number", ""))}</td>'
            f'<td>{html.escape(r.get("title", ""))}</td>'
            f'<td>{html.escape(r.get("date_approved", ""))}</td>'
            f'<td>{fiscal}</td>'
            f'<td>{res_source}</td>'
            f'</tr>'
        )
    return rows


def _build_executive_rows(issuances: list) -> list:
    rows = []
    for e in issuances:
        date = html.escape(e.get("date", "")) if e.get("date") else "—"
        rows.append(
            f'<tr>'
            f'<td>{html.escape(e.get("title", ""))}</td>'
            f'<td>{date}</td>'
            f'<td>{html.escape(e.get("authority", ""))}</td>'
            f'<td>{html.escape(e.get("description", ""))}</td>'
            f'</tr>'
        )
    return rows


def _build_fiscal_cards(fiscal_data: list) -> list:
    cards = []
    for fc in fiscal_data:
        amount = fc.get("amount", 0)
        if amount >= 1_000_000:
            amount_str = f'₱{amount / 1_000_000:,.1f}M'
        else:
            amount_str = f'₱{amount:,.0f}'
        type_label = fc.get("type", "").replace("_", " ").title()
        cards.append(
            f'<div class="card fiscal-card">'
            f'<h3>{html.escape(type_label)}</h3>'
            f'<p class="figure">{amount_str}</p>'
            f'<p class="source-label">{html.escape(fc.get("period", ""))}</p>'
            f'<p>{html.escape(fc.get("scope", ""))}</p>'
            f'<span class="source-label">{html.escape(fc.get("legislative_basis", ""))}</span>'
            f'</div>'
        )
    return cards


def _build_trend_cards(trends: list) -> list:
    cards = []
    for i, tr in enumerate(trends, 1):
        bullets_html = "".join(f'<li>{html.escape(b)}</li>' for b in tr.get("bullets", []))
        ordinances = tr.get("ordinances", [])
        refs = " · ".join(html.escape(o) for o in ordinances)
        cards.append(
            f'<div class="trend-step">'
            f'<div class="n">{i}</div>'
            f'<div class="trend-body">'
            f'<h4>{html.escape(tr.get("title", ""))}</h4>'
            f'<ul class="trend-bullets">{bullets_html}</ul>'
            f'<span class="trend-refs">{refs}</span>'
            f'</div>'
            f'</div>'
        )
    return cards


def _build_process_steps(process_list: list) -> list:
    steps = []
    total = len(process_list)
    for s in process_list:
        step_num = s.get("step", 1)
        final_class = ' final' if step_num == total else ''
        steps.append(
            f'<div class="step{final_class}">'
            f'<div class="n">{step_num}</div>'
            f'<h4>{html.escape(s.get("title", ""))}</h4>'
            f'<p>{html.escape(s.get("description", ""))}</p>'
            f'</div>'
        )
    return steps


def _format_fiscal_value(value, decimals=0) -> str:
    if value is None:
        return "—"
    try:
        if decimals == 0:
            return f'₱{int(value):,}'
        return f'₱{float(value):,.{decimals}f}'
    except (ValueError, TypeError):
        return "—"


def _get_status_class(status: str) -> str:
    if status == "enacted":
        return "pill-enacted"
    if status == "pending":
        return "pill-pending"
    return "pill"


def _build_source_link(url: str) -> str:
    if url and url.startswith(("http://", "https://")):
        return f'<a href="{html.escape(url)}" target="_blank" rel="noopener">Source &rarr;</a>'
    return "—"


# ---------------------------------------------------------------------------
# Barangay data generation
# ---------------------------------------------------------------------------

def validate_barangays(barangays: list[dict]) -> list[dict]:
    """Validate and normalize barangay entries. Returns cleaned list."""
    required = {"slug", "name", "punong_barangay"}
    seen_slugs = set()
    normalized = []
    for brgy in barangays:
        slug = brgy.get("slug", "")
        if slug in seen_slugs:
            print(f"  WARNING: duplicate barangay slug '{slug}' - skipping duplicate")
            continue
        if slug:
            seen_slugs.add(slug)
        missing = required - brgy.keys()
        if missing:
            print(f"  WARNING: barangay '{brgy.get('name', '?')}' missing fields: {missing}")
        normalized.append({
            "slug": brgy.get("slug", ""),
            "name": brgy.get("name", ""),
            "pop2024": brgy.get("pop2024", ""),
            "pop2020": brgy.get("pop2020", ""),
            "landUse": brgy.get("landUse", ""),
            "history": brgy.get("history", ""),
            "history_source": brgy.get("history_source", brgy.get("source", "")),
            "punong_barangay": brgy.get("punong_barangay", ""),
            "kagawads": brgy.get("kagawads", []),
            "officials": brgy.get("officials", []),
            "facebook": brgy.get("facebook", ""),
            "phone": brgy.get("phone", ""),
        })
    return normalized


def generate_barangays() -> None:
    """Generate barangay-data.js for homepage from JSON data."""
    data_path = SRC_DATA / "barangays.json"
    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"ERROR: Malformed JSON in {data_path}: {e}")
    barangays = validate_barangays(data.get("barangays", []))

    js_data = [{
        "slug": brgy.get("slug", ""),
        "name": brgy.get("name", ""),
        "pop2024": brgy.get("pop2024", ""),
        "pop2020": brgy.get("pop2020", ""),
        "landUse": brgy.get("landUse", ""),
        "history": brgy.get("history", ""),
        "source": brgy.get("history_source", brgy.get("source", "")),
        "punong": brgy.get("punong_barangay", ""),
        "kagawads": brgy.get("kagawads", []),
        "officials": brgy.get("officials", []),
        "facebook": brgy.get("facebook", ""),
        "phone": brgy.get("phone", ""),
    } for brgy in barangays]

    js_content = "// Auto-generated from barangays.json — do not edit manually\nvar BARANGAY_DATA = " + json.dumps(js_data, ensure_ascii=False, indent=2) + ";\n"
    (ROOT / "assets" / "barangay-data.js").write_text(js_content)


# ---------------------------------------------------------------------------
# Translation linter
# ---------------------------------------------------------------------------

TRANSLATION_ALLOWLIST = {
    "bettermapandan.org", "better mapandan", "github", "chart.js", "chart",
    "open-meteo", "lucide", "svg", "pdf", "html", "css", "json", "js",
    "philhealth", "pag-ibig", "gsis", "sss", "dswd", "doe", "da", "dar",
    "denr", "dilg", "doj", "dof", "dbm", "neda", "psa", "comelec", "coe",
    "coe-id", "philsys", "lgu", "bplo", "cenro", "menro", "ldrrmo", "lydo",
    "sk", "sb", "rtc", "mctc", "mdrrmo", "aics", "pwd", "solo parent",
    "birth certificate", "death certificate", "marriage certificate",
    "certificate of", "clearance", "barangay", "mayor",
    "mapandan", "pangasinan", "philippines", "luzon",
    "cy 2020", "cy 2021", "cy 2022", "cy 2023", "cy 2024", "cy 2025", "cy 2026",
    "res.", "res no.", "ordinance", "resolution", "executive order",
    "republic act", "ra no.", "pd no.", "bp no.", " eo ",
    "land bank", "landbank", "coa", "sglg", "fdp", "gf",
    "unpkg.com", "cdn.jsdelivr.net",
    "google maps", "google.com", "maps.app",
    "16.03", "120.456", "openstreetmap",
    "©", "© 2024", "© 2025", "© 2026",
}


def _strip_tags_for_comparison(html_text: str) -> str:
    """Remove HTML tags and normalize whitespace for translation comparison."""
    import re as _re
    text = _re.sub(r"<script[^>]*>.*?</script>", "", html_text, flags=_re.DOTALL)
    text = _re.sub(r"<style[^>]*>.*?</style>", "", text, flags=_re.DOTALL)
    text = _re.sub(r"<[^>]+>", " ", text)
    return _re.sub(r"\s+", " ", text).strip()


def _extract_text_segments(text: str, min_len: int = 20) -> list:
    """Split text into sentence segments."""
    import re as _re
    segs = _re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in segs if len(s.strip()) >= min_len]


def _is_segment_translated(seg_lower: str, fil_text_lower: str, allowlist: set) -> bool:
    """Check if a segment is likely untranslated (present in EN but not FIL)."""
    if len(seg_lower) < 25:
        return False
    if any(term in seg_lower for term in allowlist):
        return False
    return seg_lower in fil_text_lower


def _compare_file_pair(en_path: Path, fil_path: Path) -> list:
    """Compare EN and FIL files, return list of untranslated segments."""
    en_text = _strip_tags_for_comparison(en_path.read_text(encoding="utf-8"))
    fil_text = _strip_tags_for_comparison(fil_path.read_text(encoding="utf-8"))
    fil_text_lower = fil_text.lower()

    findings = []
    for seg in _extract_text_segments(en_text):
        seg_lower = seg.lower().strip()
        if _is_segment_translated(seg_lower, fil_text_lower, TRANSLATION_ALLOWLIST):
            findings.append(seg[:100] + ("..." if len(seg) > 100 else ""))
    return findings


def _collect_translation_findings(en_dir: Path, fil_dir: Path) -> tuple[list, int]:
    """Collect all translation findings across all page pairs."""
    findings = []
    pages_checked = 0

    en_files = sorted(en_dir.glob("*.html"))
    en_files += sorted((en_dir / "services").glob("*.html"))
    en_files += sorted((en_dir / "support").glob("*.html"))

    for en_path in en_files:
        rel = en_path.relative_to(en_dir)
        fil_path = fil_dir / rel
        if not fil_path.exists():
            continue

        file_findings = _compare_file_pair(en_path, fil_path)
        if file_findings:
            findings.append((str(rel), file_findings))
        pages_checked += 1

    return findings, pages_checked


def verify_translations() -> None:
    """Compare EN vs FIL HTML output and flag untranslated English strings."""
    print("\n--- Translation Linter ---\n")

    fil_dir = FIL_DIR
    if not fil_dir.exists():
        print("  FIL output not found. Run build first.")
        return

    findings, pages_checked = _collect_translation_findings(ROOT, fil_dir)

    if findings:
        total_segments = sum(len(segments) for _, segments in findings)
        print(f"  Found {total_segments} potential untranslated segment(s) in {pages_checked} page pairs:\n")
        for file_path, segments in findings:
            print(f"  [{file_path}]")
            for segment in segments:
                print(f'    - "{segment}"')
        print(f"\n  Summary: {total_segments} segment(s) across {pages_checked} pages may need translation.")
    else:
        print(f"  No untranslated segments found across {pages_checked} page pairs.")


# ---------------------------------------------------------------------------
# Asset optimization
# ---------------------------------------------------------------------------

def generate_sitemap() -> None:
    """Generate sitemap.xml with hreflang alternate links for EN/FIL."""
    import datetime
    from urllib.parse import quote

    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    base_url = "https://bettermapandan.org"

    en_files = sorted(ROOT.glob("*.html")) + sorted((ROOT / "services").glob("*.html")) + sorted((ROOT / "support").glob("*.html"))
    fil_files = sorted(FIL_DIR.glob("*.html")) + sorted((FIL_DIR / "services").glob("*.html")) + sorted((FIL_DIR / "support").glob("*.html"))

    en_paths = {f.relative_to(ROOT).as_posix() for f in en_files}
    fil_paths = {f.relative_to(FIL_DIR).as_posix() for f in fil_files}
    all_paths = sorted(en_paths | fil_paths)

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]

    for path in all_paths:
        en_url = f"{base_url}/{quote(path, safe='/')}"
        fil_url = f"{base_url}/fil/{quote(path, safe='/')}"
        lines.extend([
            "  <url>",
            f"    <loc>{en_url}</loc>",
            f"    <lastmod>{today}</lastmod>",
            "    <changefreq>monthly</changefreq>",
            "    <priority>0.8</priority>",
            f'    <xhtml:link rel="alternate" hreflang="en" href="{en_url}"/>',
            f'    <xhtml:link rel="alternate" hreflang="fil" href="{fil_url}"/>',
            "  </url>",
        ])

    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  sitemap.xml: {len(all_paths)} URLs")


def generate_llms_txt() -> None:
    """Copy llms.txt to output root for AI agent discovery."""
    llms_src = ROOT / "llms.txt"
    if llms_src.exists():
        llms_content = llms_src.read_text(encoding="utf-8")
        (ROOT / "llms.txt").write_text(llms_content, encoding="utf-8")
        print("  llms.txt: copied")
    else:
        print("  llms.txt: not found, skipping")


CSS_COMMENT_RE = re.compile(r"/\*[^*]*\*+(?:[^/*][^*]*\*+)*/")
CSS_WHITESPACE_RE = re.compile(r"\s+")
CSS_BRACE_RE = re.compile(r"\s*([{}:;,])\s*")
CSS_TRAILING_RE = re.compile(r";\s*}")
CSS_LEADING_RE = re.compile(r"^\s+", re.MULTILINE)


def minify_css(css_text: str) -> str:
    """Remove CSS comments and unnecessary whitespace."""
    css = CSS_COMMENT_RE.sub("", css_text)
    css = CSS_WHITESPACE_RE.sub(" ", css)
    css = CSS_BRACE_RE.sub(r"\1", css)
    css = CSS_TRAILING_RE.sub("}", css)
    return CSS_LEADING_RE.sub("", css).strip()


def minify_assets() -> None:
    """Minify CSS and JS assets."""
    css_path = ROOT / "assets" / "style.css"
    css_min_path = ROOT / "assets" / "style.min.css"
    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")
        css_min = minify_css(css)
        css_min_path.write_text(css_min, encoding="utf-8")
        orig_size = len(css.encode("utf-8"))
        min_size = len(css_min.encode("utf-8"))
        pct = ((1 - min_size / orig_size) * 100) if orig_size > 0 else 0
        print(f"  style.css: {orig_size:,} → {min_size:,} bytes ({pct:.1f}% reduction)")


def compress_images() -> None:
    """Compress images and convert to WebP using sharp (Node.js).

    Operations:
    - JPGs in citizens-charter: compress with mozjpeg, quality 70, max-width 1200
    - PNGs in history/: compress with png compression, quality 60, max-width 1200
    - Hero images: convert to WebP (luyan.png, Pandan.jpg, plaza.jpg)
    - History PNGs: convert to WebP
    - SVG seal: extract embedded PNG and convert to WebP
    """
    compress_script = ROOT / "compress.mjs"
    script_content = r"""import sharp from "sharp";
import fs from "fs";
import path from "path";

const MAX_WIDTH = 1200;
const MAX_WIDTH_LOGO = 400;
const WEBP_QUALITY = 80;

async function compressJpg(dir) {
  const files = fs.readdirSync(dir).filter(f => f.endsWith(".jpg"));
  let totalBefore = 0, totalAfter = 0, count = 0;
  for (const file of files) {
    const filePath = path.join(dir, file);
    const before = fs.statSync(filePath).size;
    totalBefore += before;
    try {
      const img = sharp(filePath);
      const meta = await img.metadata();
      let pipeline = img.jpeg({ quality: 70, mozjpeg: true });
      if (meta.width && meta.width > MAX_WIDTH) {
        pipeline = pipeline.resize(MAX_WIDTH, null, { withoutEnlargement: true });
      }
      const buf = await pipeline.toBuffer();
      fs.writeFileSync(filePath, buf);
      totalAfter += buf.length;
      count++;
    } catch (err) {
      console.error(`  SKIP ${file}: ${err.message}`);
    }
  }
  return { count, totalBefore, totalAfter };
}

async function compressPng(dir) {
  const files = fs.readdirSync(dir).filter(f => f.endsWith(".png"));
  let totalBefore = 0, totalAfter = 0, count = 0;
  for (const file of files) {
    const filePath = path.join(dir, file);
    const before = fs.statSync(filePath).size;
    totalBefore += before;
    try {
      const img = sharp(filePath);
      const meta = await img.metadata();
      let pipeline = img.png({ quality: 60, compressionLevel: 9 });
      if (meta.width && meta.width > MAX_WIDTH) {
        pipeline = pipeline.resize(MAX_WIDTH, null, { withoutEnlargement: true });
      }
      const buf = await pipeline.toBuffer();
      fs.writeFileSync(filePath, buf);
      totalAfter += buf.length;
      count++;
    } catch (err) {
      console.error(`  SKIP ${file}: ${err.message}`);
    }
  }
  return { count, totalBefore, totalAfter };
}

async function convertToWebP(inputPath, outputPath, maxWidth) {
  try {
    const before = fs.statSync(inputPath).size;
    const img = sharp(inputPath);
    const meta = await img.metadata();
    let pipeline = img.webp({ quality: WEBP_QUALITY });
    if (meta.width && meta.width > maxWidth) {
      pipeline = pipeline.resize(maxWidth, null, { withoutEnlargement: true });
    }
    const buf = await pipeline.toBuffer();
    fs.writeFileSync(outputPath, buf);
    const after = buf.length;
    const savings = ((1 - after / before) * 100).toFixed(1);
    console.log(`  ${path.basename(inputPath)}: ${(before / 1024).toFixed(1)} KB -> ${(after / 1024).toFixed(1)} KB (${savings}% reduction)`);
    return { before, after, count: 1 };
  } catch (err) {
    console.error(`  ERROR converting ${inputPath}: ${err.message}`);
    return { before: 0, after: 0, count: 0 };
  }
}

async function extractPngFromSvg(svgPath, outputPath) {
  try {
    const svgContent = fs.readFileSync(svgPath, 'utf8');
    const base64Match = svgContent.match(/xlink:href="data:image\/png;base64,([^"]+)"/);
    if (!base64Match) {
      console.error(`  Could not find embedded PNG in ${svgPath}`);
      return { before: 0, after: 0, count: 0 };
    }
    const base64Data = base64Match[1];
    const pngBuffer = Buffer.from(base64Data, 'base64');
    fs.writeFileSync(outputPath, pngBuffer);
    console.log(`  Extracted PNG from SVG: ${path.basename(outputPath)} (${(pngBuffer.length / 1024).toFixed(1)} KB)`);
    return { before: pngBuffer.length, after: pngBuffer.length, count: 1 };
  } catch (err) {
    console.error(`  ERROR extracting from SVG ${svgPath}: ${err.message}`);
    return { before: 0, after: 0, count: 0 };
  }
}

async function main() {
  console.log("=== Optimizing images for performance ===\n");

  console.log("1. Citizen's Charter JPGs (compression)...");
  const jpg = await compressJpg("assets/citizens-charter");
  const jpgPct = ((1 - jpg.totalAfter / jpg.totalBefore) * 100).toFixed(1);
  console.log(`  JPGs: ${jpg.count} files, ${(jpg.totalBefore/1e6).toFixed(2)}MB -> ${(jpg.totalAfter/1e6).toFixed(2)}MB (${jpgPct}%)`);

  console.log("\n2. History PNGs (compression)...");
  const png = await compressPng("assets/history");
  const pngPct = ((1 - png.totalAfter / png.totalBefore) * 100).toFixed(1);
  console.log(`  PNGs: ${png.count} files, ${(png.totalBefore/1e6).toFixed(2)}MB -> ${(png.totalAfter/1e6).toFixed(2)}MB (${pngPct}%)`);

  console.log("\n3. Converting hero images to WebP...");
  const heroImages = [
    ["assets/luyan.png", "assets/luyan.webp", MAX_WIDTH],
    ["assets/Pandan.jpg", "assets/Pandan.webp", MAX_WIDTH],
    ["assets/plaza.jpg", "assets/plaza.webp", MAX_WIDTH],
  ];
  let heroTotalBefore = 0, heroTotalAfter = 0, heroCount = 0;
  for (const [input, output, maxW] of heroImages) {
    if (fs.existsSync(input)) {
      const result = await convertToWebP(input, output, maxW);
      heroTotalBefore += result.before;
      heroTotalAfter += result.after;
      heroCount += result.count;
    }
  }
  console.log(`  Hero images: ${heroCount} files, ${(heroTotalBefore/1e6).toFixed(2)}MB -> ${(heroTotalAfter/1e6).toFixed(2)}MB`);

  console.log("\n4. Extracting and converting municipal seal to WebP...");
  const tempPng = "assets/municipal-seal-temp.png";
  const svgResult = await extractPngFromSvg("assets/logo-no-white.svg", tempPng);
  let sealBefore = 0, sealAfter = 0;
  if (fs.existsSync(tempPng)) {
    const webpResult = await convertToWebP(tempPng, "assets/municipal-seal.svg", MAX_WIDTH_LOGO);
    sealBefore = webpResult.before;
    sealAfter = webpResult.after;
    fs.unlinkSync(tempPng);
  }
  console.log(`  Seal: ${(sealBefore/1e3).toFixed(1)} KB -> ${(sealAfter/1e3).toFixed(1)} KB`);

  console.log("\n5. Converting history images to WebP...");
  const historyDir = "assets/history";
  if (fs.existsSync(historyDir)) {
    const histFiles = fs.readdirSync(historyDir).filter(f => f.endsWith(".png"));
    let histWebpBefore = 0, histWebpAfter = 0, histCount = 0;
    for (const file of histFiles) {
      const inputPath = path.join(historyDir, file);
      const outputPath = path.join(historyDir, file.replace('.png', '.webp'));
      const result = await convertToWebP(inputPath, outputPath, MAX_WIDTH);
      histWebpBefore += result.before;
      histWebpAfter += result.after;
      histCount += result.count;
    }
    console.log(`  History WebP: ${histCount} files, ${(histWebpBefore/1e6).toFixed(2)}MB -> ${(histWebpAfter/1e6).toFixed(2)}MB`);
  }

  const totalBefore = jpg.totalBefore + png.totalBefore + heroTotalBefore + sealBefore + histWebpBefore;
  const totalAfter = jpg.totalAfter + png.totalAfter + heroTotalAfter + sealAfter + histWebpAfter;
  console.log(`\n=== Total: ${(totalBefore/1e6).toFixed(2)}MB -> ${(totalAfter/1e6).toFixed(2)}MB (${((1-totalAfter/totalBefore)*100).toFixed(1)}% reduction) ===`);
}

main().catch(console.error);
"""
    compress_script.write_text(script_content, encoding="utf-8")
    import subprocess

    result = subprocess.run(
        ["node", str(compress_script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    compress_script.unlink(missing_ok=True)

    if result.returncode != 0:
        print(f"  Image compression failed: {result.stderr}", file=sys.stderr)
    else:
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)


# ---------------------------------------------------------------------------
# Build helpers (refactored to reduce complexity)
# ---------------------------------------------------------------------------

def compute_asset_base(rel: Path, is_fil: bool) -> str:
    """Compute the asset base path based on page location and language."""
    depth = len(rel.parts) - 1
    if is_fil:
        return ".." * (depth + 1) if depth >= 0 else ".."
    return ".." * depth if depth > 0 else "."


def build_lang_switcher_urls(rel: Path, is_fil: bool) -> tuple[str, str]:
    """Build language switcher URLs for a page."""
    if is_fil:
        return "../" + rel.as_posix(), rel.as_posix()
    return rel.as_posix(), "fil/" + rel.as_posix()


def build_breadcrumbs(locale: dict, rel: Path, page_title: str) -> str:
    """Build breadcrumb HTML for a page."""
    depth = len(rel.parts) - 1
    if depth <= 0:
        return ""
    bc_items = [
        f'<a href="../index.html">{t(locale, "nav.home", "Home")}</a>',
        f'<a href="../{rel.parts[0]}.html">{rel.parts[0].replace("-", " ").title()}</a>',
        f'<span aria-current="page">{page_title}</span>',
    ]
    return '<nav class="breadcrumb" aria-label="Breadcrumb">' + " &rsaquo; ".join(bc_items) + "</nav>\n"


def build_header(locale: dict, asset_base: str, is_fil: bool, en_url: str, fil_url: str) -> str:
    """Build the site header with navigation and locale strings."""
    header_raw = (SRC_PARTIALS / "header.html").read_text(encoding="utf-8")
    return fill(header_raw, {
        "ASSET_BASE": asset_base,
        "NAV_HOME": t(locale, "nav.home", "Home"),
        "NAV_SERVICES": t(locale, "nav.services", "Services"),
        "NAV_GOVERNMENT": t(locale, "nav.government", "Government"),
        "NAV_LEGISLATIVE": t(locale, "nav.legislative", "Legislative"),
        "NAV_STATISTICS": t(locale, "nav.statistics", "Statistics"),
        "NAV_TRANSPARENCY": t(locale, "nav.transparency", "Transparency"),
        "NAV_ABOUT": t(locale, "nav.about", "About"),
        "NAV_SEARCH": t(locale, "nav.search", "Search"),
        "NAV_MENU": t(locale, "nav.menu", "Menu"),
        "EMERGENCY_LABEL": t(locale, "emergency.label", "Emergency"),
        "EMERGENCY_MDRRMO": t(locale, "emergency.mdrrmo", "MDRRMO"),
        "EMERGENCY_FIRE": t(locale, "emergency.fire", "Fire (BFP)"),
        "EMERGENCY_POLICE": t(locale, "emergency.police", "Police (PNP)"),
        "LANG_EN_URL": en_url,
        "LANG_FIL_URL": fil_url,
        "LANG_ACTIVE_EN": "" if is_fil else "active",
        "LANG_ACTIVE_FIL": "active" if is_fil else "",
        "LANG_LABEL_EN": t(locale, "lang_switch.en", "EN"),
        "LANG_LABEL_FIL": t(locale, "lang_switch.fil", "FIL"),
    })


def build_footer(locale: dict, asset_base: str) -> str:
    """Build the site footer with locale strings."""
    footer_raw = (SRC_PARTIALS / "footer.html").read_text(encoding="utf-8")
    return fill(footer_raw, {
        "ASSET_BASE": asset_base,
        **SITE_CONFIG,
        "NAV_HOME": t(locale, "nav.home", "Home"),
        "NAV_SERVICES": t(locale, "nav.services", "Services"),
        "NAV_GOVERNMENT": t(locale, "nav.government", "Government"),
        "NAV_LEGISLATIVE": t(locale, "nav.legislative", "Legislative"),
        "NAV_STATISTICS": t(locale, "nav.statistics", "Statistics"),
        "NAV_TRANSPARENCY": t(locale, "nav.transparency", "Transparency"),
        "NAV_ABOUT": t(locale, "nav.about", "About"),
        "FOOTER_BRAND_DESC": t(locale, "footer.brand_desc", ""),
        "FOOTER_QUICK_LINKS": t(locale, "footer.quick_links", "Quick Links"),
        "FOOTER_RESOURCES": t(locale, "footer.resources", "Resources"),
        "FOOTER_PROJECT": t(locale, "footer.project", "Project"),
        "FOOTER_SITEMAP": t(locale, "footer.sitemap", "Sitemap"),
        "FOOTER_FAQ": t(locale, "footer.faq", "FAQ"),
        "FOOTER_SOURCE_CODE": t(locale, "footer.source_code", "Source Code (GitHub)"),
        "FOOTER_PRIVACY": t(locale, "footer.privacy", "Privacy Policy"),
        "FOOTER_TERMS": t(locale, "footer.terms", "Terms of Use"),
        "FOOTER_ACCESSIBILITY": t(locale, "footer.accessibility", "Accessibility"),
        "FOOTER_REPORT": t(locale, "footer.report", "Report Incorrect Info"),
        "FOOTER_COPYRIGHT": t(locale, "footer.copyright", ""),
        "FOOTER_COMMUNITY": t(locale, "footer.community", ""),
        "FOOTER_COST": t(locale, "footer.cost", "Cost to the People of Mapandan:"),
        "FOOTER_COST_AMOUNT": t(locale, "footer.cost_amount", "₱0"),
        "FOOTER_MUNICIPALITY": t(locale, "footer.municipality_of", "Municipality of Mapandan"),
        "FOOTER_PROVINCE": t(locale, "footer.province_of", "Province of Pangasinan"),
        "FOOTER_COA": t(locale, "footer.coa", "Commission on Audit"),
        "FOOTER_PSA": t(locale, "footer.psa", "Philippine Statistics Authority"),
    })


def resolve_body_placeholders(body: str, locale: dict, asset_base: str) -> str:
    """Resolve all locale placeholders in page body content."""
    return fill(body, {
        "ASSET_BASE": asset_base,
        ** _build_page_body_labels(locale),
    })


def _build_page_body_labels(locale: dict) -> dict:
    return {
        "ABOUT_CONTRIBUTE_CODE": t(locale, "about.contribute_code", ""),
        "ABOUT_CONTRIBUTE_GET_INVOLVED": t(locale, "about.contribute_get_involved", ""),
        "ABOUT_CONTRIBUTE_REPORT": t(locale, "about.contribute_report", ""),
        "ABOUT_CONTRIBUTE_SHARE": t(locale, "about.contribute_share", ""),
        "ABOUT_CONTRIBUTE_VERIFY": t(locale, "about.contribute_verify", ""),
        "ABOUT_DISCLAIMER_NOTICE": t(locale, "about.disclaimer_notice", ""),
        "ABOUT_GEOGRAPHY": t(locale, "about.geography", ""),
        "ABOUT_HISTORY": t(locale, "about.history", ""),
        "ABOUT_HISTORY_ERA1": t(locale, "about.history_era1", ""),
        "ABOUT_HISTORY_ERA2": t(locale, "about.history_era2", ""),
        "ABOUT_HISTORY_ERA3": t(locale, "about.history_era3", ""),
        "ABOUT_HISTORY_ERA5": t(locale, "about.history_era5", ""),
        "ABOUT_HISTORY_TITLE": t(locale, "about.history_title", ""),
        "ABOUT_MUNICIPALITY_TITLE": t(locale, "about.municipality_title", ""),
        "ABOUT_PHOTO_BRIDGE": t(locale, "about.photo_bridge", ""),
        "ABOUT_PHOTO_MARKET": t(locale, "about.photo_market", ""),
        "ABOUT_PHOTO_OFFICIALS": t(locale, "about.photo_officials", ""),
        "ABOUT_PHOTO_PLAZA": t(locale, "about.photo_plaza", ""),
        "ABOUT_PHOTO_SCHOOL": t(locale, "about.photo_school", ""),
        "ABOUT_POPULATION_GROWTH": t(locale, "about.population_growth", ""),
        "ABOUT_POPULATION_SUBTITLE": t(locale, "about.population_subtitle", ""),
        "ABOUT_PROJECT_HOW": t(locale, "about.project_how", ""),
        "ABOUT_PROJECT_MISSION": t(locale, "about.project_mission", ""),
        "ABOUT_PROJECT_OPEN_SOURCE": t(locale, "about.project_open_source", ""),
        "ABOUT_PROJECT_VOLUNTEER": t(locale, "about.project_volunteer", ""),
        "ABOUT_PROJECT_WHAT": t(locale, "about.project_what", ""),
        "ABOUT_READ_MORE": t(locale, "about.read_more", ""),
        "ABOUT_SHOW_LESS": t(locale, "about.show_less", ""),
        "ABOUT_TITLE": t(locale, "about.title", ""),
        "COMMON_COMMUNITY_VERIFIED": t(locale, "common.community_verified", ""),
        "COMMON_MUNICIPAL_ESTIMATE": t(locale, "common.municipal_estimate", ""),
        "COMMON_NEEDS_VERIFICATION": t(locale, "common.needs_verification", ""),
        "COMMON_OFFICIAL": t(locale, "common.official", ""),
        "COMMON_PLACEHOLDER": t(locale, "common.placeholder", ""),
        "COMMON_PROVINCIAL_ESTIMATE": t(locale, "common.provincial_estimate", ""),
        "COMMON_STATUTORY": t(locale, "common.statutory", ""),
        "COMMON_UNOFFICIAL": t(locale, "common.unofficial", ""),
        "COMMON_VERIFIED": t(locale, "common.verified", ""),
        "EMERGENCY_FIRE": t(locale, "emergency.fire", ""),
        "EMERGENCY_LABEL": t(locale, "emergency.label", ""),
        "EMERGENCY_MDRRMO": t(locale, "emergency.mdrrmo", ""),
        "EMERGENCY_POLICE": t(locale, "emergency.police", ""),
        "GOVERNMENT_BARANGAY_COUNCILS_TITLE": t(locale, "government.barangay_councils_title", ""),
        "GOVERNMENT_CONTACT_COL_LANDLINE": t(locale, "government.contact_col_landline", ""),
        "GOVERNMENT_CONTACT_COL_MOBILE": t(locale, "government.contact_col_mobile", ""),
        "GOVERNMENT_CONTACT_COL_OFFICE": t(locale, "government.contact_col_office", ""),
        "GOVERNMENT_CONTACT_TITLE": t(locale, "government.contact_title", ""),
        "GOVERNMENT_DEPARTMENTS_TITLE": t(locale, "government.departments_title", ""),
        "GOVERNMENT_DEPT_COL_ACRONYM": t(locale, "government.dept_col_acronym", ""),
        "GOVERNMENT_DEPT_COL_LOCATION": t(locale, "government.dept_col_location", ""),
        "GOVERNMENT_DEPT_COL_OFFICE": t(locale, "government.dept_col_office", ""),
        "GOVERNMENT_EXECUTIVE_TITLE": t(locale, "government.executive_title", ""),
        "GOVERNMENT_EXTERNAL_TITLE": t(locale, "government.external_title", ""),
        "GOVERNMENT_LEGISLATIVE_TITLE": t(locale, "government.legislative_title", ""),
        "HERO_BROWSE_SERVICES": t(locale, "hero.browse_services", ""),
        "HERO_EYEBROW": t(locale, "hero.eyebrow", ""),
        "HERO_SEARCH_TITLE": t(locale, "hero.search_title", ""),
        "HERO_SEE_BUDGET": t(locale, "hero.see_budget", ""),
        "HERO_TITLE": t(locale, "hero.title", ""),
        "ACTION_HUB_SERVICES": t(locale, "action_hub.services", "Services"),
        "ACTION_HUB_BUDGET": t(locale, "action_hub.budget", "Budget"),
        "ACTION_HUB_LEGISLATION": t(locale, "action_hub.legislation", "Legislation"),
        "ACTION_HUB_HOTLINES": t(locale, "action_hub.hotlines", "Hotlines"),
        "HERO_LEDE": t(locale, "hero.subtitle", ""),
        "HERO_SEARCH_DESC": t(locale, "hero.search_desc", ""),
        "HERO_SEARCH_PLACEHOLDER": t(locale, "hero.search_placeholder", ""),
        "HERO_SEARCH_POPULAR": t(locale, "hero.search_popular", "Popular:"),
        ** _build_homepage_labels(locale),
        ** _build_statistics_labels(locale),
        ** _build_transparency_labels(locale),
        ** _build_search_labels(locale),
    }


def _build_homepage_labels(locale: dict) -> dict:
    return {
        "HOMEPAGE_AGRI_TITLE": t(locale, "homepage.agri_title", ""),
        "HOMEPAGE_BARANGAY_EYEBROW": t(locale, "homepage.barangay_eyebrow", ""),
        "HOMEPAGE_BARANGAY_TITLE": t(locale, "homepage.barangay_title", ""),
        "HOMEPAGE_CULTURAL_EYEBROW": t(locale, "homepage.cultural_eyebrow", ""),
        "HOMEPAGE_CULTURAL_TITLE": t(locale, "homepage.cultural_title", ""),
        "HOMEPAGE_EMERGENCY_BFP": t(locale, "homepage.emergency_bfp", ""),
        "HOMEPAGE_EMERGENCY_EYEBROW": t(locale, "homepage.emergency_eyebrow", ""),
        "HOMEPAGE_EMERGENCY_HOSPITAL": t(locale, "homepage.emergency_hospital", ""),
        "HOMEPAGE_EMERGENCY_MDRRMO_DESC": t(locale, "homepage.emergency_mdrmmo_desc", ""),
        "HOMEPAGE_EMERGENCY_PNP": t(locale, "homepage.emergency_pnp", ""),
        "HOMEPAGE_EMERGENCY_RHU": t(locale, "homepage.emergency_rhu", ""),
        "HOMEPAGE_EMERGENCY_TITLE": t(locale, "homepage.emergency_title", ""),
        "HOMEPAGE_EMERGENCY_WATER": t(locale, "homepage.emergency_water", ""),
        "HOMEPAGE_EXPLORE_EYEBROW": t(locale, "homepage.explore_eyebrow", ""),
        "HOMEPAGE_EXPLORE_TITLE": t(locale, "homepage.explore_title", ""),
        "HOMEPAGE_HISTORY_CTA": t(locale, "homepage.history_cta", ""),
        "HOMEPAGE_HISTORY_EYEBROW": t(locale, "homepage.history_eyebrow", ""),
        "HOMEPAGE_HISTORY_TITLE": t(locale, "homepage.history_title", ""),
        "HOMEPAGE_LEADERSHIP_CTA": t(locale, "homepage.leadership_cta", ""),
        "HOMEPAGE_LEADERSHIP_EYEBROW": t(locale, "homepage.leadership_eyebrow", ""),
        "HOMEPAGE_LEADERSHIP_TITLE": t(locale, "homepage.leadership_title", ""),
        "HOMEPAGE_MAP_TITLE": t(locale, "homepage.map_title", ""),
        "HOMEPAGE_MUNICIPALITY_AGRI": t(locale, "homepage.municipality_agri", ""),
        "HOMEPAGE_MUNICIPALITY_FOUNDED": t(locale, "homepage.municipality_founded", ""),
        "HOMEPAGE_MUNICIPALITY_REESTABLISHED": t(locale, "homepage.municipality_reestablished", ""),
        "HOMEPAGE_MUNICIPALITY_TITLE": t(locale, "homepage.municipality_title", ""),
        "HOMEPAGE_PLAZA_TITLE": t(locale, "homepage.plaza_title", ""),
        "HOMEPAGE_WEATHER_TITLE": t(locale, "homepage.weather_title", ""),
        "HOMEPAGE_MUNICIPALITY_EYEBROW": t(locale, "homepage.municipality_eyebrow", ""),
        "HOMEPAGE_MUNICIPALITY_DESC": t(locale, "homepage.municipality_desc", ""),
        "HOMEPAGE_FOUNDED_DESC": t(locale, "homepage.founded_desc", ""),
        "HOMEPAGE_REESTABLISHED_DESC": t(locale, "homepage.reestablished_desc", ""),
        "HOMEPAGE_AGRI_DESC_FULL": t(locale, "homepage.agri_desc_full", ""),
        "HOMEPAGE_HISTORY_SUBTITLE": t(locale, "homepage.history_subtitle", ""),
        "HOMEPAGE_MILESTONE1_ERA": t(locale, "homepage.milestone1_era", ""),
        "HOMEPAGE_MILESTONE1_TITLE": t(locale, "homepage.milestone1_title", ""),
        "HOMEPAGE_MILESTONE1_DESC": t(locale, "homepage.milestone1_desc", ""),
        "HOMEPAGE_MILESTONE2_ERA": t(locale, "homepage.milestone2_era", ""),
        "HOMEPAGE_MILESTONE2_TITLE": t(locale, "homepage.milestone2_title", ""),
        "HOMEPAGE_MILESTONE2_DESC": t(locale, "homepage.milestone2_desc", ""),
        "HOMEPAGE_MILESTONE3_ERA": t(locale, "homepage.milestone3_era", ""),
        "HOMEPAGE_MILESTONE3_TITLE": t(locale, "homepage.milestone3_title", ""),
        "HOMEPAGE_MILESTONE3_DESC": t(locale, "homepage.milestone3_desc", ""),
        "HOMEPAGE_MILESTONE4_ERA": t(locale, "homepage.milestone4_era", ""),
        "HOMEPAGE_MILESTONE4_TITLE": t(locale, "homepage.milestone4_title", ""),
        "HOMEPAGE_MILESTONE4_DESC": t(locale, "homepage.milestone4_desc", ""),
        "HOMEPAGE_BARANGAY_SUBTITLE": t(locale, "homepage.barangay_subtitle", ""),
        "HOMEPAGE_SOURCES_TITLE": t(locale, "homepage.sources_title", "Sources & Historical Notes"),
        "HOMEPAGE_SOURCES_DESC": t(locale, "homepage.sources_desc", ""),
        "HOMEPAGE_PANDAN_TITLE": t(locale, "homepage.pandan_title", "Pandan Festival"),
        "HOMEPAGE_PANDAN_DESC": t(locale, "homepage.pandan_desc", ""),
        "HOMEPAGE_PANDAN_CREDIT": t(locale, "homepage.pandan_credit", ""),
        "HOMEPAGE_PLAZA_DESC": t(locale, "homepage.plaza_desc", ""),
        "HOMEPAGE_PLAZA_CREDIT": t(locale, "homepage.plaza_credit", ""),
        "HOMEPAGE_AGRI_DESC": t(locale, "homepage.agri_desc", ""),
        "HOMEPAGE_AGRI_CREDIT": t(locale, "homepage.agri_credit", ""),
        "HOMEPAGE_MAYOR_NAME": t(locale, "homepage.mayor_name", ""),
        "HOMEPAGE_MAYOR_ROLE": t(locale, "homepage.mayor_role", "Municipal Mayor"),
        "HOMEPAGE_MAYOR_AFFIL": t(locale, "homepage.mayor_affil", ""),
        "HOMEPAGE_VICE_MAYOR_NAME": t(locale, "homepage.vice_mayor_name", ""),
        "HOMEPAGE_VICE_MAYOR_ROLE": t(locale, "homepage.vice_mayor_role", "Vice Mayor &middot; Presiding Officer"),
        "HOMEPAGE_VICE_MAYOR_AFFIL": t(locale, "homepage.vice_mayor_affil", "Independent (IND)"),
        "HOMEPAGE_LEADER_SOURCE": t(locale, "homepage.leader_source", "Source: Mapandan.gov.ph"),
        "HOMEPAGE_WEATHER_LOADING": t(locale, "homepage.weather_loading", "Loading weather data..."),
        "HOMEPAGE_WEATHER_CTA": t(locale, "homepage.weather_cta", "View PAGASA Advisories &rarr;"),
        "HOMEPAGE_MAP_CTA": t(locale, "homepage.map_cta", "Open in Google Maps &rarr;"),
        "STATS_BARANGAYS": t(locale, "stats.barangays", ""),
        "STATS_DENSITY": t(locale, "stats.density", ""),
        "STATS_HOUSEHOLDS": t(locale, "stats.households", ""),
        "STATS_LAND_AREA": t(locale, "stats.land_area", ""),
        "STATS_RESIDENTS": t(locale, "stats.residents", ""),
    }


def _build_statistics_labels(locale: dict) -> dict:
    return {
        "STATISTICS_AGRI_CROPS": t(locale, "statistics.agri_crops", ""),
        "STATISTICS_AGRI_IRRIGATED": t(locale, "statistics.agri_irrigated", ""),
        "STATISTICS_AGRI_TITLE": t(locale, "statistics.agri_title", ""),
        "STATISTICS_CHART_DOWNLOAD": t(locale, "statistics.chart_download", ""),
        "STATISTICS_CHART_POP_TREND": t(locale, "statistics.chart_pop_trend", ""),
        "STATISTICS_ECON_AGRI_EMP": t(locale, "statistics.econ_agri_emp", ""),
        "STATISTICS_ECON_DYNAMISM": t(locale, "statistics.econ_dynamism", ""),
        "STATISTICS_ECON_LABOR": t(locale, "statistics.econ_labor", ""),
        "STATISTICS_ECON_POVERTY": t(locale, "statistics.econ_poverty", ""),
        "STATISTICS_ECON_TITLE": t(locale, "statistics.econ_title", ""),
        "STATISTICS_FISCAL_BALANCE_2025": t(locale, "statistics.fiscal_balance_2025", ""),
        "STATISTICS_FISCAL_BLGF": t(locale, "statistics.fiscal_blgf", ""),
        "STATISTICS_FISCAL_BLGF_TITLE": t(locale, "statistics.fiscal_blgf_title", ""),
        "STATISTICS_FISCAL_EXP_2025": t(locale, "statistics.fiscal_exp_2025", ""),
        "STATISTICS_FISCAL_REV_2025": t(locale, "statistics.fiscal_rev_2025", ""),
        "STATISTICS_FISCAL_TITLE": t(locale, "statistics.fiscal_title", ""),
        "STATISTICS_GROWTH_TITLE": t(locale, "statistics.growth_title", ""),
        "STATISTICS_LAND_BARANGAYS": t(locale, "statistics.land_barangays", ""),
        "STATISTICS_LAND_EYEBROW": t(locale, "statistics.land_eyebrow", ""),
        "STATISTICS_LAND_TITLE": t(locale, "statistics.land_title", ""),
        "STATISTICS_LAND_TOTAL": t(locale, "statistics.land_total", ""),
        "STATISTICS_LAND_URBAN_RURAL": t(locale, "statistics.land_urban_rural", ""),
        "STATISTICS_POP_DENSITY": t(locale, "statistics.pop_density", ""),
        "STATISTICS_POP_HOUSEHOLDS": t(locale, "statistics.pop_households", ""),
        "STATISTICS_POP_TITLE": t(locale, "statistics.pop_title", ""),
        "STATISTICS_POP_TOTAL": t(locale, "statistics.pop_total", ""),
        "STATISTICS_TITLE": t(locale, "statistics.title", ""),
        "STATISTICS_TRENDS_TITLE": t(locale, "statistics.trends_title", ""),
    }


def _build_transparency_labels(locale: dict) -> dict:
    return {
        "TRANSPARENCY_APPROPRIATIONS_EYEBROW": t(locale, "transparency.appropriations_eyebrow", ""),
        "TRANSPARENCY_APPROPRIATIONS_TITLE": t(locale, "transparency.appropriations_title", ""),
        "TRANSPARENCY_AUDIT_TITLE": t(locale, "transparency.audit_title", ""),
        "TRANSPARENCY_BALANCE_ASSETS": t(locale, "transparency.balance_assets", ""),
        "TRANSPARENCY_BALANCE_EYEBROW": t(locale, "transparency.balance_eyebrow", ""),
        "TRANSPARENCY_BALANCE_LIABILITIES": t(locale, "transparency.balance_liabilities", ""),
        "TRANSPARENCY_BALANCE_NET": t(locale, "transparency.balance_net", ""),
        "TRANSPARENCY_BALANCE_TITLE": t(locale, "transparency.balance_title", ""),
        "TRANSPARENCY_BUDGET_2026": t(locale, "transparency.budget_2026", ""),
        "TRANSPARENCY_BUDGET_TREND_EYEBROW": t(locale, "transparency.budget_trend_eyebrow", ""),
        "TRANSPARENCY_CAPEX_EYEBROW": t(locale, "transparency.capex_eyebrow", ""),
        "TRANSPARENCY_CAPEX_TITLE": t(locale, "transparency.capex_title", ""),
        "TRANSPARENCY_COMPLIANCE_COA": t(locale, "transparency.compliance_coa", ""),
        "TRANSPARENCY_COMPLIANCE_FDP": t(locale, "transparency.compliance_fdp", ""),
        "TRANSPARENCY_COMPLIANCE_SGLG": t(locale, "transparency.compliance_sglg", ""),
        "TRANSPARENCY_COMPLIANCE_TITLE": t(locale, "transparency.compliance_title", ""),
        "TRANSPARENCY_CREDIT_EYEBROW": t(locale, "transparency.credit_eyebrow", ""),
        "TRANSPARENCY_CREDIT_TITLE": t(locale, "transparency.credit_title", ""),
        "TRANSPARENCY_EXPENDITURE_2025": t(locale, "transparency.expenditure_2025", ""),
        "TRANSPARENCY_EXTERNAL_EYEBROW": t(locale, "transparency.external_eyebrow", ""),
        "TRANSPARENCY_EXTERNAL_TITLE": t(locale, "transparency.external_title", ""),
        "TRANSPARENCY_FISCAL_DEV_FUND": t(locale, "transparency.fiscal_dev_fund", ""),
        "TRANSPARENCY_FISCAL_LDRRMF": t(locale, "transparency.fiscal_ldrrmf", ""),
        "TRANSPARENCY_FISCAL_NTA": t(locale, "transparency.fiscal_nta", ""),
        "TRANSPARENCY_FISCAL_PS_CAP": t(locale, "transparency.fiscal_ps_cap", ""),
        "TRANSPARENCY_FISCAL_SEF": t(locale, "transparency.fiscal_sef", ""),
        "TRANSPARENCY_FISCAL_SNAPSHOT_TITLE": t(locale, "transparency.fiscal_snapshot_title", ""),
        "TRANSPARENCY_FISCAL_STRUCTURE_EYEBROW": t(locale, "transparency.fiscal_structure_eyebrow", ""),
        "TRANSPARENCY_FISCAL_STRUCTURE_TITLE": t(locale, "transparency.fiscal_structure_title", ""),
        "TRANSPARENCY_HISTORICAL_EYEBROW": t(locale, "transparency.historical_eyebrow", ""),
        "TRANSPARENCY_HISTORICAL_INC_OPS": t(locale, "transparency.historical_inc_ops", ""),
        "TRANSPARENCY_HISTORICAL_MOOE": t(locale, "transparency.historical_mooe", ""),
        "TRANSPARENCY_HISTORICAL_TAX_REV": t(locale, "transparency.historical_tax_rev", ""),
        "TRANSPARENCY_HISTORICAL_TITLE": t(locale, "transparency.historical_title", ""),
        "TRANSPARENCY_HISTORICAL_TOTAL_EQUITY": t(locale, "transparency.historical_total_equity", ""),
        "TRANSPARENCY_HISTORICAL_TOTAL_OP_EXP": t(locale, "transparency.historical_total_op_exp", ""),
        "TRANSPARENCY_HISTORICAL_TOTAL_OP_INC": t(locale, "transparency.historical_total_op_inc", ""),
        "TRANSPARENCY_PROCUREMENT_EYEBROW": t(locale, "transparency.procurement_eyebrow", ""),
        "TRANSPARENCY_PROCUREMENT_TITLE": t(locale, "transparency.procurement_title", ""),
        "TRANSPARENCY_REVENUE_2025": t(locale, "transparency.revenue_2025", ""),
        "TRANSPARENCY_REVENUE_TITLE": t(locale, "transparency.revenue_title", ""),
        "TRANSPARENCY_SOCIAL_AGRI": t(locale, "transparency.social_agri", ""),
        "TRANSPARENCY_SOCIAL_EYEBROW": t(locale, "transparency.social_eyebrow", ""),
        "TRANSPARENCY_SOCIAL_TITLE": t(locale, "transparency.social_title", ""),
        "TRANSPARENCY_TITLE": t(locale, "transparency.title", ""),
    }


def _build_search_labels(locale: dict) -> dict:
    return {
        "SEARCH_TITLE": t(locale, "search_page.title", ""),
        "SEARCH_SUBTITLE": t(locale, "search_page.subtitle", ""),
        "SEARCH_BROWSE_EYEBROW": t(locale, "search_page.browse_eyebrow", ""),
        "SEARCH_BROWSE_TITLE": t(locale, "search_page.browse_title", ""),
        "SEARCH_POPULAR_TITLE": t(locale, "search_page.popular_title", ""),
        "SEARCH_POPULAR_BIZ": t(locale, "search_page.popular_biz", ""),
        "SEARCH_POPULAR_CIVIL": t(locale, "search_page.popular_civil", ""),
        "SEARCH_POPULAR_HEALTH": t(locale, "search_page.popular_health", ""),
        "SEARCH_POPULAR_WELFARE": t(locale, "search_page.popular_welfare", ""),
        "REPORT_CHOOSE_TITLE": t(locale, "report_hub.choose_title", ""),
        "REPORT_ERROR": t(locale, "report_hub.report_error", ""),
        "REPORT_SUBMIT_INFO": t(locale, "report_hub.submit_info", ""),
        "REPORT_SUGGEST_FEATURE": t(locale, "report_hub.suggest_feature", ""),
        "REPORT_NEXT_TITLE": t(locale, "report_hub.next_title", ""),
        "REPORT_VERIFICATION_TITLE": t(locale, "report_hub.verification_title", ""),
    }


def build_hero(meta: dict, page_hero_raw: str, asset_base: str) -> str:
    """Build hero HTML if page has hero metadata."""
    if not any(meta.get(k) for k in ("hero_eyebrow", "hero_heading", "hero_lede")):
        return ""
    return fill(page_hero_raw, {
        "ASSET_BASE": asset_base,
        "HERO_EYEBROW": meta.get("hero_eyebrow", ""),
        "HERO_HEADING": meta.get("hero_heading", ""),
        "HERO_LEDE": meta.get("hero_lede", ""),
    })


def assemble_page(base: str, asset_base: str, title: str, description: str, header: str, body: str, footer: str, lang_code: str, page_url: str = "") -> str:
    """Assemble a complete page from its components."""
    base_url = "https://bettermapandan.org"
    if page_url:
        canonical = f"{base_url}/{page_url}" if not page_url.startswith("http") else page_url
    else:
        canonical = base_url
    return fill(base, {
        "ASSET_BASE": asset_base,
        "TITLE": title,
        "DESCRIPTION": description,
        "HEADER": header,
        "BODY": body,
        "FOOTER": footer,
        "LANG_ATTR": f' lang="{lang_code}"',
        "CANONICAL_URL": canonical,
    })


def build_search_entry(rel: Path, title: str, description: str, body: str, is_fil: bool, anchors_key: str = "") -> dict:
    """Build a search index entry from page content."""
    url = compute_url(rel)
    if is_fil:
        url = "fil/" + url
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


# ---------------------------------------------------------------------------
# Main build orchestrator (refactored)
# ---------------------------------------------------------------------------

def build() -> None:
    generate_barangays()

    en_locale = load_locale("en")
    fil_locale = load_locale("fil")

    base = (SRC_PARTIALS / "base.html").read_text(encoding="utf-8")
    page_hero_raw = (SRC_PARTIALS / "page-hero.html").read_text(encoding="utf-8")

    if FIL_DIR.exists():
        shutil.rmtree(FIL_DIR)

    all_search_entries = []

    for lang_code, out_root, is_fil in LANGUAGES:
        locale = en_locale if not is_fil else fil_locale
        print(f"\n--- Building [{lang_code.upper()}] ---")

        svc_pages, svc_meta, svc_hero_meta = generate_services(locale, lang_code, is_fil)
        leg_html, leg_meta, leg_hero_meta = generate_legislative(locale, is_fil)
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
    assets_dst = FIL_DIR / "assets"
    if assets_src.exists():
        if assets_dst.exists():
            shutil.rmtree(assets_dst)
        shutil.copytree(assets_src, assets_dst)
        print("\n  Copied assets to fil/assets/")

    generate_sitemap()
    generate_llms_txt()
    print(f"\nDone. {count * 2} page(s) written ({count} EN + {count} FIL)")


def _process_static_page(
    lang_code: str, locale: dict, rel: Path, meta: dict, body: str,
    base: str, page_hero_raw: str, out_root: Path, search_entries: list
) -> int:
    asset_base = compute_asset_base(rel, is_fil=(lang_code == "fil"))
    en_url, fil_url = build_lang_switcher_urls(rel, is_fil=(lang_code == "fil"))
    page_title = meta["title"].split(" —")[0].split(" |")[0].strip()
    breadcrumbs = build_breadcrumbs(locale, rel, page_title)
    header = build_header(locale, asset_base, lang_code == "fil", en_url, fil_url)
    footer = build_footer(locale, asset_base)
    hero_html = build_hero(meta, page_hero_raw, asset_base)
    body = resolve_body_placeholders(hero_html + body, locale, asset_base)
    page_url = f"fil/{rel}" if lang_code == "fil" else str(rel)
    page_html = assemble_page(base, asset_base, meta["title"], meta["description"], header, breadcrumbs + body, footer, lang_code, page_url)

    out_path = out_root / rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page_html, encoding="utf-8")
    print(f"  [{lang_code.upper()}] built {rel}  ({len(page_html):,} bytes)")

    search_entries.append(build_search_entry(rel, meta["title"], meta["description"], body, lang_code == "fil", rel.name))
    return 1


def _process_generated_page(
    lang_code: str, locale: dict, rel: Path, body_content: str, page_meta: dict, hero_meta: dict,
    base: str, page_hero_raw: str, out_root: Path, search_entries: list
) -> int:
    asset_base = compute_asset_base(rel, is_fil=(lang_code == "fil"))
    en_url, fil_url = build_lang_switcher_urls(rel, is_fil=(lang_code == "fil"))
    page_title = rel.stem.replace("-", " ").title()
    breadcrumbs = build_breadcrumbs(locale, rel, page_title)
    header = build_header(locale, asset_base, lang_code == "fil", en_url, fil_url)
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

    page_url = f"fil/{rel_path_str}" if lang_code == "fil" else rel_path_str
    page_html = assemble_page(
        base, asset_base,
        page_meta.get(rel_path_str, {}).get("title", "Better Mapandan"),
        page_meta.get(rel_path_str, {}).get("description", ""),
        header, breadcrumbs + body_content, footer, lang_code, page_url
    )

    out_path = out_root / rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page_html, encoding="utf-8")
    print(f"  [{lang_code.upper()}] built {rel}  ({len(page_html):,} bytes)")

    search_entries.append(build_search_entry(rel, rel.stem.replace("-", " ").title(), "", body_content, lang_code == "fil"))
    return 1


if __name__ == "__main__":
    if "--compress" in sys.argv:
        compress_images()
    if "--verify-translations" in sys.argv:
        verify_translations()
    if "--compress" not in sys.argv and "--verify-translations" not in sys.argv:
        build()
