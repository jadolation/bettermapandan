import re
from pathlib import Path

from _build.config import ROOT, SRC_PARTIALS, SRC_TEMPLATES, FRONT_MATTER_RE


def to_folder_index(rel: Path) -> Path:
    """Convert page.html -> page/index.html, keep index.html as-is."""
    if rel.name == "index.html":
        return rel
    return rel.parent / rel.stem / "index.html"


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



def compute_asset_base(rel: Path, is_fil: bool) -> str:
    depth = len(rel.parts) - 1
    if depth <= 0:
        return "."
    return "/".join([".."] * depth)

def compute_url(rel_path: Path) -> str:
    return "/".join(rel_path.parts)
