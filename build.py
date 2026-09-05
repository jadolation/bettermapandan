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
    Section 1: Imports & constants              (lines 14-63)
    Section 2: Locale helpers                   (lines 65-88)
    Section 3: Template utilities               (lines 90-123)
    Section 4: Service generator                (lines 125-320)
    Section 5: Legislative generator            (lines 322-479)
    Section 6: Barangay data generator          (lines 481-511)
    Section 7: Translation linter               (lines 513-611)
    Section 8: Image compression                (lines 613-673)
    Section 9: Main build function              (lines 675-1627)
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

FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)


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
    val = locale
    for p in parts:
        if isinstance(val, dict) and p in val:
            val = val[p]
        else:
            return default
    return val if val else default


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
    except Exception:
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

def generate_services(locale: dict, lang: str, is_fil: bool) -> tuple[dict[str, str], dict[str, dict]]:
    """Generate service detail pages and directory page.
    Returns (pages, metadata) where pages is {relative_path: html_content}
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

    by_category = {}
    for svc in services:
        by_category.setdefault(svc.get("category", ""), []).append(svc)

    pages = {}
    meta = {}

    # Service page labels from locale
    svc_labels = {
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

    for svc in services:
        cat = categories.get(svc.get("category", ""), {})

        # Use translated names if available
        svc_name = svc.get("name_fil", svc.get("name", ""))
        svc_desc = svc.get("description_fil", svc.get("description", ""))
        cat_name = cat.get("name_fil", cat.get("name", "")) if is_fil else cat.get("name", "")
        hero_lede = svc.get("hero_lede_fil", svc.get("hero_lede", svc_desc)) if is_fil else svc.get("hero_lede", svc.get("description", ""))

        reqs_html = "\n".join(
            f"            <li>{html.escape(r)}</li>" for r in svc.get("requirements", [])
        )
        proc_html = "\n".join(
            f"            <li>{html.escape(p)}</li>" for p in svc.get("procedure", [])
        )

        related_html = ""
        related = svc.get("related", [])
        if related:
            links = []
            for rel_slug in related:
                rel_svc = next((s for s in services if s.get("slug") == rel_slug), None)
                if rel_svc:
                    rel_name = rel_svc.get("name_fil", rel_svc.get("name", "Unknown Service")) if is_fil else rel_svc.get("name", "Unknown Service")
                    links.append(
                        f'<a href="{html.escape(rel_slug)}.html">{html.escape(rel_name)}</a>'
                    )
            related_html = (
                '<div class="service-links">\n'
                + "\n".join(f"          {link}" for link in links)
                + "\n        </div>"
            )
        else:
            related_html = f'<p>{svc_labels["SVC_NO_RELATED"]}</p>'

        photo_html = ""
        photo_ref = svc.get("photo-referenced", "")
        if photo_ref:
            photo_filename = photo_ref.split("/")[-1]
            img_prefix = "../" if not is_fil else "../../"
            photo_html = f'''
            <figure class="service-photo-container" style="margin: 2rem 0; text-align: center;">
                <img src="{img_prefix}{photo_ref}" alt="{html.escape(svc_name)} Reference" 
                    style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);" 
                    loading="lazy" 
                    onerror="this.style.display='none'; this.nextElementSibling.style.display='none';">
                <figcaption style="font-size: 0.875rem; color: #666; margin-top: 0.5rem; font-style: italic;">
                    Reference: {html.escape(photo_filename)}
                </figcaption>
            </figure>'''

        filled = fill(
            svc_template,
            {
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
                **svc_labels,
            },
        )

        svc_slug = svc.get("slug", "unknown")
        pages[f"services/{svc_slug}.html"] = filled
        meta[f"services/{svc_slug}.html"] = {
            "title": f"{svc_name} — BetterMapandan.org",
            "description": svc_desc[:160],
        }

    # --- Generate directory page ---
    category_cards = []
    for cat in data.get("categories", []):
        cat_services = by_category.get(cat.get("slug", ""), [])
        cat_name = cat.get("name_fil", cat.get("name", "")) if is_fil else cat.get("name", "")
        cat_desc = cat.get("description_fil", cat.get("description", "")) if is_fil else cat.get("description", "")

        service_links = []
        for s in cat_services:
            s_name = s.get("name_fil", s.get("name", "")) if is_fil else s.get("name", "")
            name_html = html.escape(s_name)
            time_html = html.escape(s.get("processing_time", "")) if s.get("processing_time") else ""
            fee_html = html.escape(s.get("fee", "")) if s.get("fee") else ""
            meta_html = ""
            if time_html or fee_html:
                parts = []
                if time_html:
                    parts.append(f'<span class="service-link-time">{time_html}</span>')
                if fee_html:
                    parts.append(f'<span class="service-link-fee">{fee_html}</span>')
                meta_html = f'<div class="service-link-meta">{"".join(parts)}</div>'
            service_links.append(
                f'<div class="service-link-wrap">'
                f'<a class="service-link" href="services/{html.escape(s.get("slug", ""))}.html">{name_html}</a>'
                f'{meta_html}</div>'
            )

        card = (
            f'      <div class="card service-category-card">\n'
            f'        <div class="service-card-head">\n'
            f'          <div class="service-icon"><i data-lucide="{html.escape(cat.get("icon", ""))}"></i></div>\n'
            f'          <h3>{html.escape(cat_name)}</h3>\n'
            f'        </div>\n'
            f'        <p>{html.escape(cat_desc)}</p>\n'
            f'        <div class="service-links">\n'
            + "\n".join(f"          {link}" for link in service_links)
            + f"\n        </div>\n"
            f'      </div>'
        )
        category_cards.append(card)

    dir_filled = fill(
        dir_template,
        {
            "CATEGORY_CARDS": "\n".join(category_cards),
            "SVC_TITLE": t(locale, "services_dir.title", "Services"),
            "SVC_EYEBROW": t(locale, "services_dir.eyebrow", "Citizen's Charter"),
            "SVC_LEDE": t(locale, "services_dir.lede", "Every service Mapandan offers."),
            "SVC_DESC": t(locale, "services_dir.desc", "Find the service you need."),
            "SVC_SEARCH_PLACEHOLDER": t(locale, "services_dir.search_placeholder", "Search services..."),
            "SVC_NO_RESULTS": t(locale, "services_dir.no_results", "No services match your search."),
            "SVC_BROWSE_ALL": t(locale, "services_dir.browse_all", "browse all categories"),
            "SVC_NATIONAL_EYEBROW": t(locale, "services_dir.national_eyebrow", "National Platforms"),
            "SVC_NATIONAL_TITLE": t(locale, "services_dir.national_title", "Online services"),
            "SVC_NATIONAL_DESC": t(locale, "services_dir.national_desc", "Several national government services are available online."),
            "SVC_PHILSYS": t(locale, "services_dir.national_philsys", "PhilSys National ID"),
            "SVC_PHILSYS_DESC": t(locale, "services_dir.national_philsys_desc", ""),
            "SVC_PSA": t(locale, "services_dir.national_psa", "PSA Serbilis"),
            "SVC_PSA_DESC": t(locale, "services_dir.national_psa_desc", ""),
            "SVC_EGOV": t(locale, "services_dir.national_egov", "eGovPH"),
            "SVC_EGOV_DESC": t(locale, "services_dir.national_egov_desc", ""),
            "SVC_ELGU": t(locale, "services_dir.national_elgu", "e-LGU Portal"),
            "SVC_ELGU_DESC": t(locale, "services_dir.national_elgu_desc", ""),
        },
    )

    pages["services.html"] = dir_filled
    meta["services.html"] = {
        "title": t(locale, "services_dir.title", "Services") + " — BetterMapandan.org",
        "description": t(locale, "services_dir.desc", "Find the service you need."),
    }
    return pages, meta


# ---------------------------------------------------------------------------
# Legislative generation (locale-aware)
# ---------------------------------------------------------------------------

def generate_legislative(locale: dict, is_fil: bool) -> tuple[str, dict]:
    """Generate legislative page HTML. Returns (html, metadata) for SEO."""
    data_path = SRC_DATA / "legislative.json"
    try:
        template = (SRC_TEMPLATES / "legislative.html").read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(f"ERROR: Template file not found: {SRC_TEMPLATES / 'legislative.html'}")

    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"ERROR: Malformed JSON in {data_path}: {e}")

    category_labels = data.get("category_labels", {})

    ord_rows = []
    for o in data.get("ordinances", []):
        cat_label = category_labels.get(o.get("category", ""), o.get("category", "").title())
        fiscal_val = o.get("fiscal_value")
        if fiscal_val is not None:
            try:
                fiscal = f'₱{int(fiscal_val):,}'
            except (ValueError, TypeError):
                fiscal = "—"
        else:
            fiscal = "—"
        status_val = o.get("status", "")
        status_class = "pill-enacted" if status_val == "enacted" else ("pill-pending" if status_val == "pending" else "pill")
        status_text = status_val.title()
        source_url = o.get("source_url", "")
        if source_url and source_url.startswith(("http://", "https://")):
            source = f'<a href="{html.escape(source_url)}" target="_blank" rel="noopener">Source &rarr;</a>'
        else:
            source = "—"
        cat_class = html.escape(o.get("category", ""))
        ord_rows.append(
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

    res_rows = []
    for r in data.get("resolutions", []):
        fiscal_val = r.get("fiscal_value")
        if fiscal_val is not None:
            try:
                fiscal = f'₱{float(fiscal_val):,.2f}'
            except (ValueError, TypeError):
                fiscal = "—"
        else:
            fiscal = "—"
        res_source_url = r.get("source_url", "")
        if res_source_url and res_source_url.startswith(("http://", "https://")):
            res_source = f'<a href="{html.escape(res_source_url)}" target="_blank" rel="noopener">Source &rarr;</a>'
        else:
            res_source = "—"
        res_rows.append(
            f'<tr>'
            f'<td>{html.escape(r.get("number", ""))}</td>'
            f'<td>{html.escape(r.get("title", ""))}</td>'
            f'<td>{html.escape(r.get("date_approved", ""))}</td>'
            f'<td>{fiscal}</td>'
            f'<td>{res_source}</td>'
            f'</tr>'
        )

    exec_rows = []
    for e in data.get("executive_issuances", []):
        date = html.escape(e.get("date", "")) if e.get("date") else "—"
        exec_rows.append(
            f'<tr>'
            f'<td>{html.escape(e.get("title", ""))}</td>'
            f'<td>{date}</td>'
            f'<td>{html.escape(e.get("authority", ""))}</td>'
            f'<td>{html.escape(e.get("description", ""))}</td>'
            f'</tr>'
        )

    fiscal_cards = []
    for fc in data.get("fiscal", []):
        amount = fc.get("amount", 0)
        if amount >= 1_000_000:
            amount_str = f'₱{amount / 1_000_000:,.1f}M'
        else:
            amount_str = f'₱{amount:,.0f}'
        type_label = fc.get("type", "").replace("_", " ").title()
        fiscal_cards.append(
            f'<div class="card fiscal-card">'
            f'<h3>{html.escape(type_label)}</h3>'
            f'<p class="figure">{amount_str}</p>'
            f'<p class="source-label">{html.escape(fc.get("period", ""))}</p>'
            f'<p>{html.escape(fc.get("scope", ""))}</p>'
            f'<span class="source-label">{html.escape(fc.get("legislative_basis", ""))}</span>'
            f'</div>'
        )

    trend_cards = []
    for i, tr in enumerate(data.get("legislative_trends", []), 1):
        bullets_html = ""
        for b in tr.get("bullets", []):
            bullets_html += f'<li>{html.escape(b)}</li>'
        ordinances = tr.get("ordinances", [])
        refs = " · ".join(html.escape(o) for o in ordinances)
        trend_cards.append(
            f'<div class="trend-step">'
            f'<div class="n">{i}</div>'
            f'<div class="trend-body">'
            f'<h4>{html.escape(tr.get("title", ""))}</h4>'
            f'<ul class="trend-bullets">{bullets_html}</ul>'
            f'<span class="trend-refs">{refs}</span>'
            f'</div>'
            f'</div>'
        )

    process_steps = []
    process_list = data.get("legislative_process", [])
    for s in process_list:
        step_num = s.get("step", 1)
        final_class = ' final' if step_num == len(process_list) else ''
        process_steps.append(
            f'<div class="step{final_class}">'
            f'<div class="n">{step_num}</div>'
            f'<h4>{html.escape(s.get("title", ""))}</h4>'
            f'<p>{html.escape(s.get("description", ""))}</p>'
            f'</div>'
        )

    gw = data.get("governance_framework", {})

    filled = fill(template, {
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
        # Legislative locale labels
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
    })

    return filled, {
        "title": t(locale, "legislative.ord_title", "Municipal ordinances") + " — BetterMapandan.org",
        "description": t(locale, "legislative.ord_desc", "Ordinances, resolutions, and executive issuances for the Municipality of Mapandan."),
    }


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

    js_data = []
    for brgy in barangays:
        js_data.append({
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
        })

    js_content = "// Auto-generated from barangays.json — do not edit manually\nvar BARANGAY_DATA = " + json.dumps(js_data, ensure_ascii=False, indent=2) + ";\n"
    js_path = ROOT / "assets" / "barangay-data.js"
    js_path.write_text(js_content)


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def verify_translations() -> None:
    """Compare EN vs FIL HTML output and flag untranslated English strings."""
    import re as _re

    def strip_tags(html_text: str) -> str:
        """Remove HTML tags and collapse whitespace."""
        text = _re.sub(r"<script[^>]*>.*?</script>", "", html_text, flags=_re.S)
        text = _re.sub(r"<style[^>]*>.*?</style>", "", html_text, flags=_re.S)
        text = _re.sub(r"<[^>]+>", " ", text)
        text = _re.sub(r"\s+", " ", text).strip()
        return text

    def extract_segments(text: str, min_len: int = 20) -> list[str]:
        """Split into sentence-like segments."""
        segs = _re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in segs if len(s.strip()) >= min_len]

    # Words/phrases that are expected to stay English (proper nouns, tech terms, etc.)
    ALLOWLIST = {
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
        "chart.js", "unpkg.com", "cdn.jsdelivr.net",
        "google maps", "google.com", "maps.app",
        "16.03", "120.456", "openstreetmap",
        "©", "© 2024", "© 2025", "© 2026",
    }

    print("\n--- Translation Linter ---\n")

    en_dir = ROOT
    fil_dir = FIL_DIR

    if not fil_dir.exists():
        print("  FIL output not found. Run build first.")
        return

    # Collect all EN HTML files
    en_files = sorted(en_dir.glob("*.html")) + sorted((en_dir / "services").glob("*.html")) + sorted((en_dir / "support").glob("*.html"))
    findings = []
    pages_checked = 0

    for en_path in en_files:
        rel = en_path.relative_to(en_dir)
        fil_path = fil_dir / rel

        if not fil_path.exists():
            continue

        en_text = strip_tags(en_path.read_text(encoding="utf-8"))
        fil_text = strip_tags(fil_path.read_text(encoding="utf-8"))

        en_segs = extract_segments(en_text)
        fil_segs = extract_segments(fil_text)

        # Find EN segments that also appear verbatim in FIL (untranslated)
        for seg in en_segs:
            seg_lower = seg.lower().strip()
            # Skip very short or trivial segments
            if len(seg_lower) < 25:
                continue
            # Skip if in allowlist
            if any(term in seg_lower for term in ALLOWLIST):
                continue
            # Check if this exact segment appears in FIL text
            if seg_lower in fil_text.lower():
                # Truncate for display
                display = seg[:100] + ("..." if len(seg) > 100 else "")
                findings.append((str(rel), display))

        pages_checked += 1

    if findings:
        print(f"  Found {len(findings)} potential untranslated segment(s) in {pages_checked} page pairs:\n")
        prev_file = None
        for file_path, segment in findings:
            if file_path != prev_file:
                print(f"  [{file_path}]")
                prev_file = file_path
            print(f"    - \"{segment}\"")
        print(f"\n  Summary: {len(findings)} segment(s) across {pages_checked} pages may need translation.")
        print("  Note: Some matches are expected (proper nouns, technical terms). Review manually.")
    else:
        print(f"  No untranslated segments found across {pages_checked} page pairs.")


def generate_sitemap() -> None:
    """Generate sitemap.xml with hreflang alternate links for EN/FIL."""
    import datetime
    from urllib.parse import quote

    today = datetime.date.today().isoformat()
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

        lines.append("  <url>")
        lines.append(f"    <loc>{en_url}</loc>")
        lines.append(f"    <lastmod>{today}</lastmod>")
        lines.append(f"    <changefreq>monthly</changefreq>")
        lines.append(f"    <priority>0.8</priority>")
        lines.append(f'    <xhtml:link rel="alternate" hreflang="en" href="{en_url}"/>')
        lines.append(f'    <xhtml:link rel="alternate" hreflang="fil" href="{fil_url}"/>')
        lines.append("  </url>")

    lines.append("</urlset>")

    sitemap_path = ROOT / "sitemap.xml"
    sitemap_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  sitemap.xml: {len(all_paths)} URLs")


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
    css = CSS_LEADING_RE.sub("", css)
    return css.strip()


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
    """Compress citizen's charter JPGs and history PNGs using sharp (Node.js)."""
    compress_script = ROOT / "compress.mjs"
    script_content = r"""import sharp from "sharp";
import fs from "fs";
import path from "path";

async function compressDir(dir, ext, method, params) {
  const files = fs.readdirSync(dir).filter(f => f.endsWith(ext));
  let totalBefore = 0, totalAfter = 0, count = 0;
  for (const file of files) {
    const filePath = path.join(dir, file);
    const before = fs.statSync(filePath).size;
    totalBefore += before;
    try {
      const buf = await sharp(filePath)[method](params).toBuffer();
      fs.writeFileSync(filePath, buf);
      totalAfter += buf.length;
      count++;
    } catch (err) {
      console.error(`  SKIP ${file}: ${err.message}`);
    }
  }
  return { count, totalBefore, totalAfter };
}

async function main() {
  console.log("=== Compressing images ===\n");
  const jpg = await compressDir("assets/citizens-charter", ".jpg", "jpeg", { quality: 82, mozjpeg: true });
  const jpgPct = ((1 - jpg.totalAfter / jpg.totalBefore) * 100).toFixed(1);
  console.log(`  JPGs: ${jpg.count} files, ${(jpg.totalBefore/1e6).toFixed(1)}MB → ${(jpg.totalAfter/1e6).toFixed(1)}MB (${jpgPct}%)`);

  const png = await compressDir("assets/history", ".png", "png", { quality: 80, compressionLevel: 9 });
  const pngPct = ((1 - png.totalAfter / png.totalBefore) * 100).toFixed(1);
  console.log(`  PNGs: ${png.count} files, ${(png.totalBefore/1e6).toFixed(1)}MB → ${(png.totalAfter/1e6).toFixed(1)}MB (${pngPct}%)`);

  const totalBefore = jpg.totalBefore + png.totalBefore;
  const totalAfter = jpg.totalAfter + png.totalAfter;
  console.log(`\n  Total: ${(totalBefore/1e6).toFixed(1)}MB → ${(totalAfter/1e6).toFixed(1)}MB (${((1-totalAfter/totalBefore)*100).toFixed(1)}% reduction)`);
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
    )
    compress_script.unlink(missing_ok=True)

    if result.returncode != 0:
        print(f"  Image compression failed: {result.stderr}", file=sys.stderr)
    else:
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)


def build() -> None:
    # Generate barangay data (shared)
    generate_barangays()

    # Load locales
    en_locale = load_locale("en")
    fil_locale = load_locale("fil")

    base = (SRC_PARTIALS / "base.html").read_text(encoding="utf-8")
    header_raw = (SRC_PARTIALS / "header.html").read_text(encoding="utf-8")
    footer_raw = (SRC_PARTIALS / "footer.html").read_text(encoding="utf-8")
    page_hero_raw = (SRC_PARTIALS / "page-hero.html").read_text(encoding="utf-8")

    # Clean Filipino output directory
    if FIL_DIR.exists():
        shutil.rmtree(FIL_DIR)

    # Languages: (lang_code, locale_dict, output_root, is_fil)
    languages = [
        ("en", en_locale, ROOT, False),
        ("fil", fil_locale, FIL_DIR, True),
    ]

    all_search_entries = []

    for lang_code, locale, out_root, is_fil in languages:
        print(f"\n--- Building [{lang_code.upper()}] ---")

        # Generate services for this language
        svc_pages, svc_meta = generate_services(locale, lang_code, is_fil)

        # Generate legislative for this language
        leg_html, leg_meta = generate_legislative(locale, is_fil)
        svc_pages["legislative.html"] = leg_html
        svc_meta["legislative.html"] = leg_meta

        # Collect all .html files from src/pages/ (static pages)
        page_files = sorted(SRC_PAGES.rglob("*.html"))
        if not page_files:
            raise SystemExit(f"No page sources found in {SRC_PAGES}")

        search_entries = []
        count = 0

        # Process static pages from src/pages/
        for page_path in page_files:
            rel = page_path.relative_to(SRC_PAGES)
            meta, body = parse_page(page_path.read_text(encoding="utf-8"))

            # Compute asset base
            if is_fil:
                # Filipino pages are in /fil/, so root pages need ".." for assets
                depth = len(rel.parts) - 1
                asset_base = ".." * (depth + 1) if depth >= 0 else ".."
            else:
                depth = len(rel.parts) - 1
                asset_base = ".." * depth if depth > 0 else "."

            # Language switcher URLs
            if is_fil:
                en_url = "../" + rel.as_posix()
                fil_url = rel.as_posix()
            else:
                en_url = rel.as_posix()
                fil_url = "fil/" + rel.as_posix()

            # Breadcrumbs
            breadcrumbs = ""
            if depth > 0:
                bc_items = []
                bc_items.append(f'<a href="../index.html">{t(locale, "nav.home", "Home")}</a>')
                parent_name = rel.parts[0].replace("-", " ").title()
                parent_link = "../" + rel.parts[0] + ".html"
                bc_items.append(f'<a href="{parent_link}">{parent_name}</a>')
                current_name = meta["title"].split(" —")[0].split(" |")[0].strip()
                bc_items.append(f'<span aria-current="page">{current_name}</span>')
                breadcrumbs = (
                    '<nav class="breadcrumb" aria-label="Breadcrumb">'
                    + " &rsaquo; ".join(bc_items)
                    + "</nav>\n"
                )

            # Header with locale strings
            header = fill(header_raw, {
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
                "LANG_ACTIVE_EN": "active" if not is_fil else "",
                "LANG_ACTIVE_FIL": "active" if is_fil else "",
                "LANG_LABEL_EN": t(locale, "lang_switch.en", "EN"),
                "LANG_LABEL_FIL": t(locale, "lang_switch.fil", "FIL"),
            })

            # Footer with locale strings
            footer = fill(footer_raw, {
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

            # Hero
            hero_html = ""
            if "hero_eyebrow" in meta or "hero_heading" in meta or "hero_lede" in meta:
                hero_html = fill(
                    page_hero_raw,
                    {
                        "ASSET_BASE": asset_base,
                        "HERO_EYEBROW": meta.get("hero_eyebrow", ""),
                        "HERO_HEADING": meta.get("hero_heading", ""),
                        "HERO_LEDE": meta.get("hero_lede", ""),
                    },
                )
            body = hero_html + body

            # Resolve body placeholders (for migrated keys)
            body = fill(body, {
                "ASSET_BASE": asset_base,
                # About page
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
                # Common badges
                "COMMON_COMMUNITY_VERIFIED": t(locale, "common.community_verified", ""),
                "COMMON_MUNICIPAL_ESTIMATE": t(locale, "common.municipal_estimate", ""),
                "COMMON_NEEDS_VERIFICATION": t(locale, "common.needs_verification", ""),
                "COMMON_OFFICIAL": t(locale, "common.official", ""),
                "COMMON_PLACEHOLDER": t(locale, "common.placeholder", ""),
                "COMMON_PROVINCIAL_ESTIMATE": t(locale, "common.provincial_estimate", ""),
                "COMMON_STATUTORY": t(locale, "common.statutory", ""),
                "COMMON_UNOFFICIAL": t(locale, "common.unofficial", ""),
                "COMMON_VERIFIED": t(locale, "common.verified", ""),
                # Emergency
                "EMERGENCY_FIRE": t(locale, "emergency.fire", ""),
                "EMERGENCY_LABEL": t(locale, "emergency.label", ""),
                "EMERGENCY_MDRRMO": t(locale, "emergency.mdrrmo", ""),
                "EMERGENCY_POLICE": t(locale, "emergency.police", ""),
                # Government page
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
                # Hero
                "HERO_BROWSE_SERVICES": t(locale, "hero.browse_services", ""),
                "HERO_EYEBROW": t(locale, "hero.eyebrow", ""),
                "HERO_SEARCH_TITLE": t(locale, "hero.search_title", ""),
                "HERO_SEE_BUDGET": t(locale, "hero.see_budget", ""),
                "HERO_TITLE": t(locale, "hero.title", ""),
                # Homepage
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
                # Homepage - new keys
                "ACTION_HUB_SERVICES": t(locale, "action_hub.services", "Services"),
                "ACTION_HUB_BUDGET": t(locale, "action_hub.budget", "Budget"),
                "ACTION_HUB_LEGISLATION": t(locale, "action_hub.legislation", "Legislation"),
                "ACTION_HUB_HOTLINES": t(locale, "action_hub.hotlines", "Hotlines"),
                "HERO_LEDE": t(locale, "hero.subtitle", ""),
                "HERO_SEARCH_DESC": t(locale, "hero.search_desc", ""),
                "HERO_SEARCH_PLACEHOLDER": t(locale, "hero.search_placeholder", ""),
                "HERO_SEARCH_POPULAR": t(locale, "hero.search_popular", "Popular:"),
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
                # Statistics page
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
                # Stats strip
                "STATS_BARANGAYS": t(locale, "stats.barangays", ""),
                "STATS_DENSITY": t(locale, "stats.density", ""),
                "STATS_HOUSEHOLDS": t(locale, "stats.households", ""),
                "STATS_LAND_AREA": t(locale, "stats.land_area", ""),
                "STATS_RESIDENTS": t(locale, "stats.residents", ""),
                # Transparency page
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
                # Search page
                "SEARCH_TITLE": t(locale, "search_page.title", ""),
                "SEARCH_SUBTITLE": t(locale, "search_page.subtitle", ""),
                "SEARCH_BROWSE_EYEBROW": t(locale, "search_page.browse_eyebrow", ""),
                "SEARCH_BROWSE_TITLE": t(locale, "search_page.browse_title", ""),
                "SEARCH_POPULAR_TITLE": t(locale, "search_page.popular_title", ""),
                "SEARCH_POPULAR_BIZ": t(locale, "search_page.popular_biz", ""),
                "SEARCH_POPULAR_CIVIL": t(locale, "search_page.popular_civil", ""),
                "SEARCH_POPULAR_HEALTH": t(locale, "search_page.popular_health", ""),
                "SEARCH_POPULAR_WELFARE": t(locale, "search_page.popular_welfare", ""),
                # Report hub
                "REPORT_CHOOSE_TITLE": t(locale, "report_hub.choose_title", ""),
                "REPORT_ERROR": t(locale, "report_hub.report_error", ""),
                "REPORT_SUBMIT_INFO": t(locale, "report_hub.submit_info", ""),
                "REPORT_SUGGEST_FEATURE": t(locale, "report_hub.suggest_feature", ""),
                "REPORT_NEXT_TITLE": t(locale, "report_hub.next_title", ""),
                "REPORT_VERIFICATION_TITLE": t(locale, "report_hub.verification_title", ""),
            })

            # Add lang attribute to html tag
            page_html = fill(
                base,
                {
                    "ASSET_BASE": asset_base,
                    "TITLE": meta["title"],
                    "DESCRIPTION": meta["description"],
                    "HEADER": header,
                    "BODY": breadcrumbs + body,
                    "FOOTER": footer,
                    "LANG_ATTR": f' lang="{lang_code}"',
                },
            )

            # Output path
            out_path = out_root / rel
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(page_html, encoding="utf-8")
            count += 1
            print(f"  [{lang_code.upper()}] built {rel}  ({len(page_html):,} bytes)")

            # Search index
            url = compute_url(rel)
            if is_fil:
                url = "fil/" + url
            plain_body = strip_html(body)

            anchors = SECTION_ANCHORS.get(rel.name, [])
            section_anchors = []
            if anchors:
                for anchor_id, heading in anchors:
                    idx = plain_body.lower().find(heading.lower())
                    if idx != -1:
                        section_anchors.append({"anchor": anchor_id, "pos": idx})
                section_anchors.sort(key=lambda s: s["pos"])

            entry = {
                "title": meta["title"],
                "url": url,
                "description": meta["description"],
                "body": plain_body,
            }
            if section_anchors:
                entry["section_anchors"] = section_anchors
            search_entries.append(entry)

        # Process generated pages (services, legislative) — strip front matter
        for rel_path, body_content in svc_pages.items():
            body_content = strip_front_matter(body_content)
            rel = Path(rel_path)

            # Compute asset base
            if is_fil:
                depth = len(rel.parts) - 1
                asset_base = ".." * (depth + 1) if depth >= 0 else ".."
            else:
                depth = len(rel.parts) - 1
                asset_base = ".." * depth if depth > 0 else "."

            # Language switcher URLs
            if is_fil:
                en_url = "../" + rel.as_posix()
                fil_url = rel.as_posix()
            else:
                en_url = rel.as_posix()
                fil_url = "fil/" + rel.as_posix()

            # Breadcrumbs
            breadcrumbs = ""
            if depth > 0:
                bc_items = []
                bc_items.append(f'<a href="../index.html">{t(locale, "nav.home", "Home")}</a>')
                parent_name = rel.parts[0].replace("-", " ").title()
                parent_link = "../" + rel.parts[0] + ".html"
                bc_items.append(f'<a href="{parent_link}">{parent_name}</a>')
                current_name = rel.stem.replace("-", " ").title()
                bc_items.append(f'<span aria-current="page">{current_name}</span>')
                breadcrumbs = (
                    '<nav class="breadcrumb" aria-label="Breadcrumb">'
                    + " &rsaquo; ".join(bc_items)
                    + "</nav>\n"
                )

            # Header
            header = fill(header_raw, {
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
                "LANG_ACTIVE_EN": "active" if not is_fil else "",
                "LANG_ACTIVE_FIL": "active" if is_fil else "",
                "LANG_LABEL_EN": t(locale, "lang_switch.en", "EN"),
                "LANG_LABEL_FIL": t(locale, "lang_switch.fil", "FIL"),
            })

            # Footer
            footer = fill(footer_raw, {
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

            # Assemble page (no hero for generated pages)
            page_meta = svc_meta.get(rel_path, {})
            page_html = fill(
                base,
                {
                    "ASSET_BASE": asset_base,
                    "TITLE": page_meta.get("title", "Better Mapandan"),
                    "DESCRIPTION": page_meta.get("description", ""),
                    "HEADER": header,
                    "BODY": breadcrumbs + body_content,
                    "FOOTER": footer,
                    "LANG_ATTR": f' lang="{lang_code}"',
                },
            )

            # For Filipino, apply string replacements
            if is_fil:
                # ... (FIL replacements will be migrated in Phase 2)
                pass

            # Output path
            out_path = out_root / rel
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(page_html, encoding="utf-8")
            count += 1
            print(f"  [{lang_code.upper()}] built {rel}  ({len(page_html):,} bytes)")

            # Search index
            url = compute_url(rel)
            if is_fil:
                url = "fil/" + url
            plain_body = strip_html(body_content)

            entry = {
                "title": rel.stem.replace("-", " ").title(),
                "url": url,
                "description": "",
                "body": plain_body,
            }
            search_entries.append(entry)

        all_search_entries.extend(search_entries)
        print(f"  [{lang_code.upper()}] search index: {len(search_entries)} entries")

    # Write combined search index
    index_path = ROOT / "assets" / "search-index.json"
    index_path.write_text(json.dumps(all_search_entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSearch index: {len(all_search_entries)} total entries")

    # Minify CSS
    minify_assets()

    # Copy assets to Filipino output
    assets_src = ROOT / "assets"
    assets_dst = FIL_DIR / "assets"
    if assets_src.exists():
        if assets_dst.exists():
            shutil.rmtree(assets_dst)
        shutil.copytree(assets_src, assets_dst)
        print(f"\n  Copied assets to fil/assets/")

    # Generate sitemap
    generate_sitemap()

    total = count * 2  # EN + FIL (both produce same pages)
    print(f"\nDone. {total} page(s) written ({count} EN + {count} FIL)")


if __name__ == "__main__":
    if "--compress" in sys.argv:
        compress_images()
    if "--verify-translations" in sys.argv:
        verify_translations()
    if "--compress" not in sys.argv and "--verify-translations" not in sys.argv:
        build()
