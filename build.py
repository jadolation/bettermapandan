#!/usr/bin/env python3
"""
build.py — assembles the Better Mapandan static site.

Single source of truth for the header and footer lives in src/partials/.
Each page's unique content lives in src/pages/<name>.html as:

    ---
    title: <page title>
    description: <meta description>
    ---
    <body content — everything between </header> and <footer>>

Run:
    python3 build.py

Output: all pages written to the project root (ready to serve as-is).
Nested pages (e.g. services/*.html) are written to subdirectories.
A full-text search index is generated at assets/search-index.json.
"""

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC_PAGES = ROOT / "src" / "pages"
SRC_PARTIALS = ROOT / "src" / "partials"

SRC_DATA = ROOT / "src" / "data"
SRC_TEMPLATES = ROOT / "src" / "templates"
SERVICES_OUT = SRC_PAGES / "services"

SITE_CONFIG = {
    "REPO_URL": "https://github.com/jadolation/bettermapandan.git",
}

FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)


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


def strip_html(html: str) -> str:
    """Remove HTML tags and collapse whitespace for search indexing."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_section(html: str, max_chars: int = 200) -> str:
    """Extract a short plain-text summary from HTML content."""
    text = strip_html(html)
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + "..."
    return text


def compute_url(rel_path: Path) -> str:
    """Compute the output URL path relative to the site root."""
    parts = rel_path.parts
    # services/foo.html -> services/foo.html
    # support/foo.html -> support/foo.html
    # index.html -> index.html
    return "/".join(parts)


def generate_services() -> None:
    """Generate service detail pages and directory page from JSON data."""
    data_path = SRC_DATA / "services.json"
    svc_template = (SRC_TEMPLATES / "service.html").read_text(encoding="utf-8")
    dir_template = (SRC_TEMPLATES / "services-directory.html").read_text(encoding="utf-8")

    data = json.loads(data_path.read_text(encoding="utf-8"))
    services = data.get("services", [])
    categories = {c["slug"]: c for c in data.get("categories", [])}

    # Map services by category
    by_category = {}
    for svc in services:
        by_category.setdefault(svc["category"], []).append(svc)

    # Ensure output directory exists
    SERVICES_OUT.mkdir(parents=True, exist_ok=True)

    # --- Generate individual service pages ---
    for svc in services:
        cat = categories.get(svc["category"], {})

        # Build requirements list HTML
        reqs_html = "\n".join(
            f"            <li>{html.escape(r)}</li>" for r in svc.get("requirements", [])
        )
        proc_html = "\n".join(
            f"            <li>{html.escape(p)}</li>" for p in svc.get("procedure", [])
        )

        # Build related services links
        related_html = ""
        related = svc.get("related", [])
        if related:
            links = []
            for rel_slug in related:
                rel_svc = next((s for s in services if s["slug"] == rel_slug), None)
                if rel_svc:
                    links.append(
                        f'<a href="{rel_slug}.html">{html.escape(rel_svc["name"])}</a>'
                    )
            related_html = (
                '<div class="service-links">\n'
                + "\n".join(f"          {link}" for link in links)
                + "\n        </div>"
            )
        else:
            related_html = '<p>No related services available.</p>'

        # --- BUILD PHOTO REFERENCE HTML ---
        photo_html = ""
        photo_ref = svc.get("photo-referenced", "")
        if photo_ref:
            photo_filename = photo_ref.split("/")[-1]
            photo_html = f'''
            <figure class="service-photo-container" style="margin: 2rem 0; text-align: center;">
                <img src="../{photo_ref}" alt="{html.escape(svc['name'])} Reference" 
                    style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);" 
                    loading="lazy" 
                    onerror="this.style.display='none'; this.nextElementSibling.style.display='none';">
                <figcaption style="font-size: 0.875rem; color: #666; margin-top: 0.5rem; font-style: italic;">
                    Reference: {html.escape(photo_filename)}
                </figcaption>
            </figure>'''

        # Fill template placeholders
        filled = fill(
            svc_template,
            {
                "NAME": svc["name"],
                "DESCRIPTION": svc["description"],
                "CATEGORY_NAME": cat.get("name", ""),
                "HERO_LEDE": svc.get("hero_lede", svc.get("description", "")),
                "DESCRIPTION_FULL": svc.get("description_full", svc.get("description", "")),
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
                "PHOTO_HTML": photo_html,  # <-- Injected here
                "DELIVERY_MODE": svc.get("delivery_mode", "in-person"),
            },
        )

        out_path = SERVICES_OUT / f"{svc['slug']}.html"
        out_path.write_text(filled, encoding="utf-8")

    # --- Generate directory page ---
    category_cards = []
    for cat in data.get("categories", []):
        cat_services = by_category.get(cat["slug"], [])
        
        service_links = []
        for s in cat_services:
            name_html = html.escape(s["name"])
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
            f'        <div class="service-icon">{cat.get("icon", "")}</div>\n'
            f'        <h3>{html.escape(cat["name"])}</h3>\n'
            f'        <p>{html.escape(cat["description"])}</p>\n'
            f'        <div class="service-links">\n'
            + "\n".join(f"          {link}" for link in service_links)
            + f"\n        </div>\n"
            f'      </div>'
        )
        category_cards.append(card)

    dir_filled = fill(
        dir_template,
        {"CATEGORY_CARDS": "\n".join(category_cards)},
    )

    out_dir = SRC_PAGES / "services.html"
    out_dir.write_text(dir_filled, encoding="utf-8")


def generate_legislative() -> None:
    """Generate legislative page from JSON data."""
    data_path = SRC_DATA / "legislative.json"
    template = (SRC_TEMPLATES / "legislative.html").read_text(encoding="utf-8")
    data = json.loads(data_path.read_text(encoding="utf-8"))

    category_labels = data.get("category_labels", {})

    # --- Build ordinances table rows ---
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

    # --- Build resolutions table rows ---
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

    # --- Build executive issuances rows ---
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

    # --- Build fiscal cards ---
    fiscal_cards = []
    for f in data.get("fiscal", []):
        amount = f["amount"]
        if amount >= 1_000_000:
            amount_str = f'₱{amount / 1_000_000:,.1f}M'
        else:
            amount_str = f'₱{amount:,.0f}'
        type_label = f["type"].replace("_", " ").title()
        fiscal_cards.append(
            f'<div class="card fiscal-card">'
            f'<h3>{html.escape(type_label)}</h3>'
            f'<p class="figure">{amount_str}</p>'
            f'<p class="source-label">{html.escape(f["period"])}</p>'
            f'<p>{html.escape(f["scope"])}</p>'
            f'<span class="source-label">{html.escape(f["legislative_basis"])}</span>'
            f'</div>'
        )

    # --- Build trends cards (step-flow with bullets) ---
    trend_cards = []
    for i, t in enumerate(data.get("legislative_trends", []), 1):
        bullets_html = ""
        for b in t.get("bullets", []):
            bullets_html += f'<li>{html.escape(b)}</li>'
        ordinances = t.get("ordinances", [])
        refs = " · ".join(html.escape(o) for o in ordinances)
        trend_cards.append(
            f'<div class="trend-step">'
            f'<div class="n">{i}</div>'
            f'<div class="trend-body">'
            f'<h4>{html.escape(t["title"])}</h4>'
            f'<ul class="trend-bullets">{bullets_html}</ul>'
            f'<span class="trend-refs">{refs}</span>'
            f'</div>'
            f'</div>'
        )

    # --- Build process steps ---
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

    # --- Governance framework ---
    gw = data.get("governance_framework", {})

    # --- Fill template ---
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
    })

    out_path = SRC_PAGES / "legislative.html"
    out_path.write_text(filled, encoding="utf-8")


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
    out_path.write_text(filled, encoding="utf-8")


def build() -> None:
    # Generate service pages from JSON data (creates src/pages/services/*.html + src/pages/services.html)
    generate_services()
    # Generate legislative page from JSON data (creates src/pages/legislative.html)
    generate_legislative()

    base = (SRC_PARTIALS / "base.html").read_text(encoding="utf-8")
    header_raw = (SRC_PARTIALS / "header.html").read_text(encoding="utf-8")
    footer_raw = (SRC_PARTIALS / "footer.html").read_text(encoding="utf-8")
    page_hero_raw = (SRC_PARTIALS / "page-hero.html").read_text(encoding="utf-8")

    # Collect all .html files recursively under src/pages/
    page_files = sorted(SRC_PAGES.rglob("*.html"))
    if not page_files:
        sys.exit(f"No page sources found in {SRC_PAGES}")

    search_entries = []
    count = 0

    for page_path in page_files:
        # Relative path from src/pages/ (e.g. services/birth.html)
        rel = page_path.relative_to(SRC_PAGES)
        meta, body = parse_page(page_path.read_text(encoding="utf-8"))

        # Compute asset base: "." for root pages, ".." for subdirectory pages
        depth = len(rel.parts) - 1
        asset_base = ".." * depth if depth > 0 else "."

        # Fill header and footer with ASSET_BASE + SITE_CONFIG for this page
        header = fill(header_raw, {"ASSET_BASE": asset_base})
        footer = fill(footer_raw, {"ASSET_BASE": asset_base, **SITE_CONFIG})

        # Compute breadcrumbs if in a subdirectory
        breadcrumbs = ""
        if depth > 0:
            bc_items = []
            bc_items.append('<a href="../index.html">Home</a>')
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

        html = fill(
            base,
            {
                "ASSET_BASE": asset_base,
                "TITLE": meta["title"],
                "DESCRIPTION": meta["description"],
                "HEADER": header,
                "BODY": breadcrumbs + body,
                "FOOTER": footer,
            },
        )

        # Output path: maintain subdirectory structure
        out_path = ROOT / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
        count += 1
        print(f"  built {rel}  ({len(html):,} bytes)")

        # Search index entry
        url = compute_url(rel)
        search_entries.append({
            "title": meta["title"],
            "url": url,
            "description": meta["description"],
            "body": strip_html(body),
        })

    # Write search index
    index_path = ROOT / "assets" / "search-index.json"
    index_path.write_text(json.dumps(search_entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  built assets/search-index.json  ({len(search_entries)} entries)")

    print(f"\nDone. {count} page(s) written to {ROOT}/")


if __name__ == "__main__":
    build()