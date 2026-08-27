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
    svc_template = (SRC_TEMPLATES / "service.html").read_text()
    dir_template = (SRC_TEMPLATES / "services-directory.html").read_text()

    data = json.loads(data_path.read_text())
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
                # Find the service name for this slug
                rel_svc = next((s for s in services if s["slug"] == rel_slug), None)
                if rel_svc:
                    links.append(
                        f'<a href="services/{rel_slug}.html">{html.escape(rel_svc["name"])}</a>'
                    )
            related_html = (
                '<div class="service-links">\n'
                + "\n".join(f"          {link}" for link in links)
                + "\n        </div>"
            )
        else:
            related_html = '<p>No related services available.</p>'

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
            },
        )

        out_path = SERVICES_OUT / f"{svc['slug']}.html"
        out_path.write_text(filled)

    # --- Generate directory page ---
    category_cards = []
    for cat in data.get("categories", []):
        cat_services = by_category.get(cat["slug"], [])
        # Cap at 3 links per category
        service_links = []
        for s in cat_services[:3]:
            service_links.append(
                f'<a class="service-link" href="services/{s["slug"]}.html">{html.escape(s["name"])}</a>'
            )
        if len(cat_services) > 3:
            service_links.append(
                f'<a class="service-link service-link-more" href="services.html">View all {len(cat_services)} services &rarr;</a>'
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

    # Write directory page (will be processed by build() as a regular page)
    out_dir = SRC_PAGES / "services.html"
    out_dir.write_text(dir_filled)


def build() -> None:
    # Generate service pages from JSON data (creates src/pages/services/*.html + src/pages/services.html)
    generate_services()

    base = (SRC_PARTIALS / "base.html").read_text()
    header_raw = (SRC_PARTIALS / "header.html").read_text()
    footer_raw = (SRC_PARTIALS / "footer.html").read_text()
    page_hero_raw = (SRC_PARTIALS / "page-hero.html").read_text()

    # Collect all .html files recursively under src/pages/
    page_files = sorted(SRC_PAGES.rglob("*.html"))
    if not page_files:
        sys.exit(f"No page sources found in {SRC_PAGES}")

    search_entries = []
    count = 0

    for page_path in page_files:
        # Relative path from src/pages/ (e.g. services/birth.html)
        rel = page_path.relative_to(SRC_PAGES)
        meta, body = parse_page(page_path.read_text())

        # Compute asset base: "." for root pages, ".." for subdirectory pages
        depth = len(rel.parts) - 1
        asset_base = ".." * depth if depth > 0 else "."

        # Fill header and footer with ASSET_BASE + SITE_CONFIG for this page
        header = fill(header_raw, {"ASSET_BASE": asset_base})
        footer = fill(footer_raw, {"ASSET_BASE": asset_base, **SITE_CONFIG})

        # Compute breadcrumbs if in a subdirectory
        breadcrumbs = ""
        if depth > 0:
            # Build breadcrumb nav
            bc_items = []
            bc_items.append('<a href="index.html">Home</a>')
            # For services/foo.html -> parent is "Services"
            parent_name = rel.parts[0].replace("-", " ").title()
            parent_link = rel.parts[0] + ".html"
            bc_items.append(f'<a href="{parent_link}">{parent_name}</a>')
            current_name = meta["title"].split(" —")[0].split(" |")[0].strip()
            bc_items.append(f'<span aria-current="page">{current_name}</span>')
            breadcrumbs = (
                '<nav class="breadcrumb" aria-label="Breadcrumb">'
                + " &rsaquo; ".join(bc_items)
                + "</nav>\n"
            )

        # If hero_eyebrow/hero_heading/hero_lede are in front matter,
        # inject the page-hero partial instead of requiring inline hero HTML.
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
        out_path.write_text(html)
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
    index_path.write_text(json.dumps(search_entries, ensure_ascii=False, indent=2))
    print(f"  built assets/search-index.json  ({len(search_entries)} entries)")

    print(f"\nDone. {count} page(s) written to {ROOT}/")


if __name__ == "__main__":
    build()
