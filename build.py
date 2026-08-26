#!/usr/bin/env python3
"""
build.py — assembles the Better Mapandan static site.

Single source of truth for the header and footer lives in src/partials/.
Each page's unique content lives in src/pages/<name>.html as:

    ---
    title: <page <title>>
    description: <meta description>
    ---
    <body content — everything between </header> and <footer>>

Run:
    python3 build.py

Output: index.html, services.html, government.html, legislative.html,
transparency.html written to the project root (ready to serve as-is —
no further build step needed at deploy time). Nothing in assets/ is
touched; this script only assembles HTML.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC_PAGES = ROOT / "src" / "pages"
SRC_PARTIALS = ROOT / "src" / "partials"

# Single place to change the repo link that appears in every page's footer.
SITE_CONFIG = {
    "REPO_URL": "https://github.com/bettergovph",
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


def build() -> None:
    base = (SRC_PARTIALS / "base.html").read_text()
    header = (SRC_PARTIALS / "header.html").read_text()
    footer = fill((SRC_PARTIALS / "footer.html").read_text(), SITE_CONFIG)

    page_files = sorted(SRC_PAGES.glob("*.html"))
    if not page_files:
        sys.exit(f"No page sources found in {SRC_PAGES}")

    for page_path in page_files:
        meta, body = parse_page(page_path.read_text())
        html = fill(
            base,
            {
                "TITLE": meta["title"],
                "DESCRIPTION": meta["description"],
                "HEADER": header,
                "BODY": body,
                "FOOTER": footer,
            },
        )
        out_path = ROOT / page_path.name
        out_path.write_text(html)
        print(f"  built {out_path.name}  ({len(html):,} bytes)")

    print(f"\nDone. {len(page_files)} page(s) written to {ROOT}/")


if __name__ == "__main__":
    build()
