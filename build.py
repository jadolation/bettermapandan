#!/usr/bin/env python3
"""
build.py — assembles the Better Mapandan static site.

Supports dual-language output (EN at root, FIL under /fil/).
Locale strings loaded from locales/en.json and locales/fil.json.

Run:
    python3 build.py

Output: all pages written to the project root (EN) and /fil/ (FIL).
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
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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
        sys.exit("Page is missing --- front matter (title/description).")
    meta_block, body = match.groups()
    meta = {}
    for line in meta_block.splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    for required in ("title", "description"):
        if required not in meta:
            sys.exit(f"Page is missing required front matter field: {required}")
    return meta, body.strip("\n")


def fill(template: str, values: dict) -> str:
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def strip_html(html_text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html_text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def compute_url(rel_path: Path) -> str:
    return "/".join(rel_path.parts)


# ---------------------------------------------------------------------------
# Service generation (locale-aware)
# ---------------------------------------------------------------------------

def generate_services(locale: dict, lang: str, out_pages_dir: Path, is_fil: bool) -> tuple[str, str]:
    """Generate service detail pages and directory page.
    Returns (directory_html, search_entries_json_part)."""
    data_path = SRC_DATA / "services.json"
    svc_template = (SRC_TEMPLATES / "service.html").read_text(encoding="utf-8")
    dir_template = (SRC_TEMPLATES / "services-directory.html").read_text(encoding="utf-8")

    data = json.loads(data_path.read_text(encoding="utf-8"))
    services = data.get("services", [])
    categories = {c["slug"]: c for c in data.get("categories", [])}

    by_category = {}
    for svc in services:
        by_category.setdefault(svc["category"], []).append(svc)

    # Ensure output directory exists
    services_out = out_pages_dir / "services"
    services_out.mkdir(parents=True, exist_ok=True)

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
        cat = categories.get(svc["category"], {})

        # Use translated names if available
        svc_name = svc.get("name_fil", svc["name"]) if is_fil else svc["name"]
        svc_desc = svc.get("description_fil", svc["description"]) if is_fil else svc["description"]
        cat_name = cat.get("name_fil", cat.get("name", "")) if is_fil else cat.get("name", "")
        hero_lede = svc.get("hero_lede_fil", svc.get("hero_lede", svc_desc)) if is_fil else svc.get("hero_lede", svc["description"])

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
                rel_svc = next((s for s in services if s["slug"] == rel_slug), None)
                if rel_svc:
                    rel_name = rel_svc.get("name_fil", rel_svc["name"]) if is_fil else rel_svc["name"]
                    links.append(
                        f'<a href="{rel_slug}.html">{html.escape(rel_name)}</a>'
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
                "NAME": svc_name,
                "DESCRIPTION": svc_desc,
                "CATEGORY_NAME": cat_name,
                "HERO_LEDE": hero_lede,
                "DESCRIPTION_FULL": svc.get("description_full", svc["description"]),
                "REQUIREMENTS": reqs_html,
                "PROCEDURE": proc_html,
                "OFFICE": svc.get("office", ""),
                "CLASSIFICATION": svc.get("classification", ""),
                "PROCESSING_TIME": svc.get("processing_time", ""),
                "FEE": svc.get("fee", "Free"),
                "WHERE": svc.get("where_to_apply", ""),
                "CONTACT": svc.get("contact", ""),
                "SOURCE": svc.get("source", "Mapandan Citizen's Charter"),
                "LAST_UPDATED": svc.get("last_updated", "August 2025"),
                "RELATED_SERVICES": related_html,
                "PHOTO_HTML": photo_html,
                "DELIVERY_MODE": svc.get("delivery_mode", "in-person"),
                **svc_labels,
            },
        )

        out_path = services_out / f"{svc['slug']}.html"
        out_path.write_text(filled, encoding="utf-8")

    # --- Generate directory page ---
    category_cards = []
    for cat in data.get("categories", []):
        cat_services = by_category.get(cat["slug"], [])
        cat_name = cat.get("name_fil", cat.get("name", "")) if is_fil else cat.get("name", "")
        cat_desc = cat.get("description_fil", cat.get("description", "")) if is_fil else cat.get("description", "")

        service_links = []
        for s in cat_services:
            s_name = s.get("name_fil", s["name"]) if is_fil else s["name"]
            name_html = html.escape(s_name)
            time_html = html.escape(s["processing_time"]) if s.get("processing_time") else ""
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
                f'<a class="service-link" href="services/{s["slug"]}.html">{name_html}</a>'
                f'{meta_html}</div>'
            )

        card = (
            f'      <div class="card service-category-card">\n'
            f'        <div class="service-card-head">\n'
            f'          <div class="service-icon"><i data-lucide="{cat.get("icon", "")}"></i></div>\n'
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

    return dir_filled


# ---------------------------------------------------------------------------
# Legislative generation (locale-aware)
# ---------------------------------------------------------------------------

def generate_legislative(locale: dict, is_fil: bool) -> str:
    """Generate legislative page HTML. Returns filled template string."""
    data_path = SRC_DATA / "legislative.json"
    template = (SRC_TEMPLATES / "legislative.html").read_text(encoding="utf-8")
    data = json.loads(data_path.read_text(encoding="utf-8"))

    category_labels = data.get("category_labels", {})

    ord_rows = []
    for o in data.get("ordinances", []):
        cat_label = category_labels.get(o["category"], o["category"].title())
        fiscal = f'₱{o["fiscal_value"]:,.0f}' if o.get("fiscal_value") else "—"
        status_class = "pill-enacted" if o["status"] == "enacted" else ("pill-pending" if o["status"] == "pending" else "pill")
        status_text = o["status"].title()
        source = f'<a href="{o["source_url"]}" target="_blank" rel="noopener">Source &rarr;</a>' if o.get("source_url") else "—"
        ord_rows.append(
            f'<tr>'
            f'<td>{html.escape(o["number"])}</td>'
            f'<td>{html.escape(o["title"])}</td>'
            f'<td>{html.escape(o["date_enacted"])}</td>'
            f'<td><span class="category-pill category-{o["category"]}">{html.escape(cat_label)}</span></td>'
            f'<td>{html.escape(o["sp_review"])}</td>'
            f'<td><span class="pill {status_class}">{status_text}</span></td>'
            f'<td>{source}</td>'
            f'</tr>'
        )

    res_rows = []
    for r in data.get("resolutions", []):
        fiscal = f'₱{r["fiscal_value"]:,.2f}' if r.get("fiscal_value") else "—"
        source = f'<a href="{r["source_url"]}" target="_blank" rel="noopener">Source &rarr;</a>' if r.get("source_url") else "—"
        res_rows.append(
            f'<tr>'
            f'<td>{html.escape(r["number"])}</td>'
            f'<td>{html.escape(r["title"])}</td>'
            f'<td>{html.escape(r["date_approved"])}</td>'
            f'<td>{fiscal}</td>'
            f'<td>{source}</td>'
            f'</tr>'
        )

    exec_rows = []
    for e in data.get("executive_issuances", []):
        date = html.escape(e["date"]) if e.get("date") else "—"
        exec_rows.append(
            f'<tr>'
            f'<td>{html.escape(e["title"])}</td>'
            f'<td>{date}</td>'
            f'<td>{html.escape(e["authority"])}</td>'
            f'<td>{html.escape(e["description"])}</td>'
            f'</tr>'
        )

    fiscal_cards = []
    for fc in data.get("fiscal", []):
        amount = fc["amount"]
        if amount >= 1_000_000:
            amount_str = f'₱{amount / 1_000_000:,.1f}M'
        else:
            amount_str = f'₱{amount:,.0f}'
        type_label = fc["type"].replace("_", " ").title()
        fiscal_cards.append(
            f'<div class="card fiscal-card">'
            f'<h3>{html.escape(type_label)}</h3>'
            f'<p class="figure">{amount_str}</p>'
            f'<p class="source-label">{html.escape(fc["period"])}</p>'
            f'<p>{html.escape(fc["scope"])}</p>'
            f'<span class="source-label">{html.escape(fc["legislative_basis"])}</span>'
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
            f'<h4>{html.escape(tr["title"])}</h4>'
            f'<ul class="trend-bullets">{bullets_html}</ul>'
            f'<span class="trend-refs">{refs}</span>'
            f'</div>'
            f'</div>'
        )

    process_steps = []
    for s in data.get("legislative_process", []):
        final_class = ' final' if s["step"] == len(data["legislative_process"]) else ''
        process_steps.append(
            f'<div class="step{final_class}">'
            f'<div class="n">{s["step"]}</div>'
            f'<h4>{html.escape(s["title"])}</h4>'
            f'<p>{html.escape(s["description"])}</p>'
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

    return filled


# ---------------------------------------------------------------------------
# Barangay data generation
# ---------------------------------------------------------------------------

def generate_barangays() -> None:
    """Generate barangay-data.js for homepage from JSON data."""
    data_path = SRC_DATA / "barangays.json"
    data = json.loads(data_path.read_text())
    barangays = data.get("barangays", [])

    js_data = []
    for brgy in barangays:
        js_data.append({
            "slug": brgy["slug"],
            "name": brgy["name"],
            "pop2024": brgy.get("pop2024", ""),
            "pop2020": brgy.get("pop2020", ""),
            "landUse": brgy.get("landUse", ""),
            "history": brgy.get("history", ""),
            "source": brgy.get("history_source", ""),
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

    for lang_code, locale, out_root, is_fil in languages:
        print(f"\n--- Building [{lang_code.upper()}] ---")

        # Generate services for this language
        dir_html = generate_services(locale, lang_code, SRC_PAGES if not is_fil else out_root, is_fil)
        # Write directory page to src/pages so the main loop can pick it up
        (SRC_PAGES / "services.html").write_text(dir_html, encoding="utf-8")

        # Generate legislative for this language
        leg_html = generate_legislative(locale, is_fil)
        (SRC_PAGES / "legislative.html").write_text(leg_html, encoding="utf-8")

        # Collect all .html files recursively under src/pages/
        page_files = sorted(SRC_PAGES.rglob("*.html"))
        if not page_files:
            sys.exit(f"No page sources found in {SRC_PAGES}")

        search_entries = []
        count = 0

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
                en_url = "../" + rel.as_posix() if depth == 0 else "../" + "/".join([".."] * depth + [rel.as_posix()])
                fil_url = rel.as_posix() if depth == 0 else "/".join([".."] * depth + [rel.as_posix()])
                # Simpler: en is always one level up from fil
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

            # For Filipino, also replace hardcoded English text in body
            if is_fil:
                # Homepage-specific replacements
                page_html = page_html.replace(
                    '<span class="eyebrow">Independent &middot; Citizen-Maintained &middot; Pangasinan</span>',
                    f'<span class="eyebrow">{t(locale, "hero.eyebrow", "")}</span>'
                )
                page_html = page_html.replace(
                    '<h1>Mapandan, in the open.</h1>',
                    f'<h1>{t(locale, "hero.title", "")}</h1>'
                )
                page_html = page_html.replace(
                    '<a class="btn btn-primary" href="services.html">Browse Services</a>',
                    f'<a class="btn btn-primary" href="services.html">{t(locale, "hero.browse_services", "")}</a>'
                )
                page_html = page_html.replace(
                    '<a class="btn btn-ghost" href="transparency.html">See the Budget</a>',
                    f'<a class="btn btn-ghost" href="transparency.html">{t(locale, "hero.see_budget", "")}</a>'
                )
                page_html = page_html.replace(
                    '<h3>Find a Service</h3>',
                    f'<h3>{t(locale, "hero.search_title", "")}</h3>'
                )
                page_html = page_html.replace(
                    'Find a Service',
                    t(locale, "hero.search_title", "Find a Service")
                )
                # Stats labels
                page_html = page_html.replace('>Residents<', f'>{t(locale, "stats.residents", "Residents")}<')
                page_html = page_html.replace('>Barangays<', f'>{t(locale, "stats.barangays", "Barangays")}<')
                page_html = page_html.replace('>Households<', f'>{t(locale, "stats.households", "Households")}<')
                page_html = page_html.replace('>Pop. density<', f'>{t(locale, "stats.density", "Pop. density")}<')
                page_html = page_html.replace('>Land area<', f'>{t(locale, "stats.land_area", "Land area")}<')
                # Emergency
                page_html = page_html.replace('>Emergency<', f'>{t(locale, "emergency.label", "Emergency")}<')
                page_html = page_html.replace('>Fire (BFP)<', f'>{t(locale, "emergency.fire", "Fire (BFP)")}<')
                page_html = page_html.replace('>Police (PNP)<', f'>{t(locale, "emergency.police", "Police (PNP)")}<')
                page_html = page_html.replace('>MDRRMO<', f'>{t(locale, "emergency.mdrrmo", "MDRRMO")}<')
                # Homepage sections
                page_html = page_html.replace('>A Brief History<', f'>{t(locale, "homepage.history_eyebrow", "")}<')
                page_html = page_html.replace('>The Story of Mapandan<', f'>{t(locale, "homepage.history_title", "")}<')
                page_html = page_html.replace('>Cultural Heritage<', f'>{t(locale, "homepage.cultural_eyebrow", "")}<')
                page_html = page_html.replace('>Local traditions and community life<', f'>{t(locale, "homepage.cultural_title", "")}<')
                page_html = page_html.replace('>Leadership<', f'>{t(locale, "homepage.leadership_eyebrow", "")}<')
                page_html = page_html.replace('>Currently in office<', f'>{t(locale, "homepage.leadership_title", "")}<')
                page_html = page_html.replace('>Explore Mapandan<', f'>{t(locale, "homepage.explore_eyebrow", "")}<')
                page_html = page_html.replace('>Weather &amp; map<', f'>{t(locale, "homepage.explore_title", "")}<')
                page_html = page_html.replace('>Emergency Hotlines<', f'>{t(locale, "homepage.emergency_eyebrow", "")}<')
                page_html = page_html.replace('>Who to call<', f'>{t(locale, "homepage.emergency_title", "")}<')
                page_html = page_html.replace('>Current weather<', f'>{t(locale, "homepage.weather_title", "")}<')
                page_html = page_html.replace('>Interactive map<', f'>{t(locale, "homepage.map_title", "")}<')
                page_html = page_html.replace(
                    'See the full Government Directory &rarr;',
                    t(locale, "homepage.leadership_cta", "")
                )
                page_html = page_html.replace(
                    'Read the full history &amp; explore historical photos &rarr;',
                    t(locale, "homepage.history_cta", "")
                )
                page_html = page_html.replace(
                    '>Stories Behind Our Barangays<',
                    f'>{t(locale, "homepage.barangay_eyebrow", "")}<'
                )
                page_html = page_html.replace(
                    '>15 communities, 15 histories<',
                    f'>{t(locale, "homepage.barangay_title", "")}<'
                )

                # Search page
                page_html = page_html.replace(
                    '>Find government information<',
                    f'>{t(locale, "search_page.title", "")}<'
                )
                page_html = page_html.replace(
                    '>Search services, officials, ordinances, offices, and more.<',
                    f'>{t(locale, "search_page.subtitle", "")}<'
                )
                page_html = page_html.replace(
                    '>Browse by topic<',
                    f'>{t(locale, "search_page.browse_eyebrow", "")}<'
                )
                page_html = page_html.replace(
                    '>Explore Mapandan<',
                    f'>{t(locale, "search_page.browse_title", "")}<'
                )
                page_html = page_html.replace(
                    '>Popular services<',
                    f'>{t(locale, "search_page.popular_title", "")}<'
                )
                page_html = page_html.replace(
                    '>Business Permitting<',
                    f'>{t(locale, "search_page.popular_biz", "")}<'
                )
                page_html = page_html.replace(
                    '>Civil Registry<',
                    f'>{t(locale, "search_page.popular_civil", "")}<'
                )
                page_html = page_html.replace(
                    '>Health Services<',
                    f'>{t(locale, "search_page.popular_health", "")}<'
                )
                page_html = page_html.replace(
                    '>Social Welfare<',
                    f'>{t(locale, "search_page.popular_welfare", "")}<'
                )

                # Report hub
                page_html = page_html.replace(
                    '>Civic Contribution Hub<',
                    f'>{t(locale, "report_hub.title", "")}<'
                )
                page_html = page_html.replace(
                    '>Choose how you want to contribute<',
                    f'>{t(locale, "report_hub.choose_title", "")}<'
                )
                page_html = page_html.replace(
                    '>Report Error<',
                    f'>{t(locale, "report_hub.report_error", "")}<'
                )
                page_html = page_html.replace(
                    '>Submit Missing Info<',
                    f'>{t(locale, "report_hub.submit_info", "")}<'
                )
                page_html = page_html.replace(
                    '>Suggest Feature<',
                    f'>{t(locale, "report_hub.suggest_feature", "")}<'
                )
                page_html = page_html.replace(
                    '>What happens next?<',
                    f'>{t(locale, "report_hub.next_title", "")}<'
                )
                page_html = page_html.replace(
                    '>Verification status<',
                    f'>{t(locale, "report_hub.verification_title", "")}<'
                )

                # Statistics page
                page_html = page_html.replace(
                    '>Statistics &amp; Indicators<',
                    f'>{t(locale, "statistics.title", "")}<'
                )
                page_html = page_html.replace(
                    '>Demographic overview<',
                    f'>{t(locale, "statistics.pop_title", "")}<'
                )
                page_html = page_html.replace(
                    '>Economic indicators<',
                    f'>{t(locale, "statistics.econ_title", "")}<'
                )
                page_html = page_html.replace(
                    '>Local revenue &amp; expenditure<',
                    f'>{t(locale, "statistics.fiscal_title", "")}<'
                )

                # Transparency page
                page_html = page_html.replace(
                    '>Budget &amp; Fiscal Transparency<',
                    f'>{t(locale, "transparency.title", "")}<'
                )
                page_html = page_html.replace(
                    '>Current budget &amp; supplemental appropriations<',
                    f'>{t(locale, "transparency.appropriations_title", "")}<'
                )
                page_html = page_html.replace(
                    '>Loans &amp; borrowing<',
                    f'>{t(locale, "transparency.credit_title", "")}<'
                )
                page_html = page_html.replace(
                    '>Revenue breakdown<',
                    f'>{t(locale, "transparency.revenue_title", "")}<'
                )
                page_html = page_html.replace(
                    '>Governance compliance<',
                    f'>{t(locale, "transparency.compliance_title", "")}<'
                )

                # About page
                page_html = page_html.replace(
                    '>About Better Mapandan<',
                    f'>{t(locale, "about.title", "")}<'
                )
                page_html = page_html.replace(
                    '>The municipality<',
                    f'>{t(locale, "about.municipality_title", "")}<'
                )
                page_html = page_html.replace(
                    '>Mapandan through the years<',
                    f'>{t(locale, "about.history_title", "")}<'
                )
                page_html = page_html.replace(
                    '>History<',
                    f'>{t(locale, "about.history", "")}<'
                )
                page_html = page_html.replace(
                    '>Geography<',
                    f'>{t(locale, "about.geography", "")}<'
                )
                page_html = page_html.replace(
                    '>Read more<',
                    f'>{t(locale, "about.read_more", "")}<'
                )
                page_html = page_html.replace(
                    '>Show less<',
                    f'>{t(locale, "about.show_less", "")}<'
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

        # Write search index (append to shared index)
        index_path = ROOT / "assets" / "search-index.json"
        if index_path.exists():
            existing = json.loads(index_path.read_text(encoding="utf-8"))
        else:
            existing = []
        existing.extend(search_entries)
        index_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [{lang_code.upper()}] search index: {len(search_entries)} entries")

    # Copy assets to Filipino output
    assets_src = ROOT / "assets"
    assets_dst = FIL_DIR / "assets"
    if assets_src.exists():
        if assets_dst.exists():
            shutil.rmtree(assets_dst)
        shutil.copytree(assets_src, assets_dst)
        print(f"\n  Copied assets to fil/assets/")

    # Clean up intermediate generated pages from src/pages
    (SRC_PAGES / "services.html").unlink(missing_ok=True)
    (SRC_PAGES / "legislative.html").unlink(missing_ok=True)
    services_dir = SRC_PAGES / "services"
    if services_dir.exists():
        shutil.rmtree(services_dir)

    total = count * 2  # EN + FIL
    print(f"\nDone. {total} page(s) written ({count} EN + {count} FIL)")


if __name__ == "__main__":
    build()
