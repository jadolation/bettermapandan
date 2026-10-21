"""Allowlisted Pages artifact boundary: python -m _build.staging after build.

GIS resources are enumerated from the configured generated outputs, never by
copying raw input trees. Other assets and downloads retain explicit contracts.
"""
import json
import re
import shutil
from pathlib import Path

from _build.assets import JS_SOURCES
from _build.gis_sources import gis_asset_outputs
from _build.templates import to_folder_index

STAGING_DIR = "_site"
LOCALES = ("", "fil", "pag")
ROOT_FILES = ("CNAME", ".nojekyll", "robots.txt", "sitemap.xml", "llms.txt", "site.webmanifest")
PUBLIC_DATA = {
    "search-index.json", "data/audit-index.json", "data/contractor-index.json",
    "data/entity-bids.json", "data/entity-contracts.json", "data/entity-projects.json",
    "data/entity-relationships.json", "data/fund-index.json", "data/project-index.json",
    "data/transparency-csv.json",
}
MEDIA_DIRS = {"barangay-council", "citizens-charter", "history", "logos", "officials", "projects"}
MEDIA_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".ico"}
PRIVATE_PARTS = {"src", "raw", "review", "datasets", "tests", "node_modules", "__pycache__"}


def _regular_file(root: Path, rel: Path) -> Path:
    """Reject symlinks in every component, even links pointing inside the repo."""
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"Unsafe public path: {rel}")
    current = root
    for part in rel.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"Symlink is not publishable: {current}")
    if not current.is_file():
        raise ValueError(f"Missing public build output: {rel}")
    return current


def _tree_files(root: Path, rel: Path) -> list[Path]:
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"Unsafe public path: {rel}")
    directory = root / rel
    current = root
    for part in rel.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"Symlink is not publishable: {current}")
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(f"Expected a real directory: {rel}")
    files = []
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Symlink is not publishable: {path}")
        if path.is_file():
            files.append(path.relative_to(root))
        elif not path.is_dir():
            raise ValueError(f"Special file is not publishable: {path}")
    return files


def page_outputs(root: Path) -> set[Path]:
    """Mirror orchestrator: src/pages, generated services and legislative."""
    pages = {
        rel.relative_to("src/pages")
        for rel in _tree_files(root, Path("src/pages")) if rel.suffix == ".html"
    }
    if Path("index.html") not in pages:
        raise ValueError("Missing home page source")
    for page in pages:
        if any(part.startswith(".") or part.lower() in PRIVATE_PARTS for part in page.parts):
            raise ValueError(f"Unsafe page route: {page}")
        if page.parts[0] in {"assets", "fil", "pag", STAGING_DIR}:
            raise ValueError(f"Reserved page route: {page}")
    services = json.loads(_regular_file(root, Path("src/data/services.json")).read_text(encoding="utf-8"))
    pages.update((Path("services.html"), Path("legislative.html")))
    for service in services["services"]:
        slug = service.get("slug", "unknown")
        if not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise ValueError(f"Unsafe service slug: {slug!r}")
        pages.add(Path("services") / f"{slug}.html")
    return {Path(locale) / to_folder_index(page) for locale in LOCALES for page in pages}


def _is_accepted_asset(rel: Path) -> bool:
    # Social metadata uses og-image.png; keep the unused SVG source out of Pages.
    if rel == Path("og-image.svg"):
        return False
    if any(part.startswith(".") or part.lower() in PRIVATE_PARTS for part in rel.parts):
        return False
    scripts = {Path(source).relative_to("assets").as_posix() for source in JS_SOURCES}
    scripts |= {Path(source).with_suffix(".min.js").as_posix() for source in scripts}
    scripts.update({"chart.umd.min.js", "js/legislative.js"})
    media = len(rel.parts) == 1 or (len(rel.parts) == 2 and rel.parts[0] in MEDIA_DIRS)
    return (rel.as_posix() in PUBLIC_DATA | scripts
            or (media and rel.suffix.lower() in MEDIA_SUFFIXES)
            or rel.as_posix() in {"style.css", "style.min.css"}
            or (len(rel.parts) == 2 and rel.parts[0] == "css" and rel.suffix == ".css"))


def _asset_outputs(root: Path) -> set[Path]:
    outputs = set()
    for path in _tree_files(root, Path("assets")):
        rel = path.relative_to("assets")
        if _is_accepted_asset(rel):
            outputs.add(path)
    for path in gis_asset_outputs(root):
        if (not isinstance(path, Path) or path.is_absolute() or ".." in path.parts
                or path.parts[:2] != ("assets", "gis") or len(path.parts) < 3
                or any(part.startswith(".") for part in path.parts)
                or path.suffix.lower() not in {".geojson", ".json", ".png"}):
            raise ValueError(f"Unsafe generated GIS asset: {path}")
        _regular_file(root, path)
        outputs.add(path)
    return outputs


def _download_outputs(root: Path) -> set[Path]:
    data = json.loads(_regular_file(root, Path("src/data/audit-reports.json")).read_text(encoding="utf-8"))
    outputs = set()
    for entry in data["audit_archive"]:
        for document in entry["files"]:
            url = document["path"]
            if not isinstance(url, str) or not url.startswith("/datasets/"):
                raise ValueError(f"Unsafe audit download: {url!r}")
            rel = Path(url[1:])
            location = (
                rel.parts[1] == "audit-reports" and len(rel.parts) == 3
                or bool(re.fullmatch(r"Mapandan-Annual-Audit-Report-20\d{2}", rel.parts[1]))
                and len(rel.parts) in (3, 4)
                or len(rel.parts) == 2 and bool(re.fullmatch(r"Mapandan-Executive-Summary-20\d{2}\.pdf", rel.name))
            ) if len(rel.parts) >= 2 else False
            if (not location or ".." in rel.parts
                    or any(part.startswith(".") or part.lower() in PRIVATE_PARTS - {"datasets"} for part in rel.parts)
                    or rel.suffix.lower() not in {".pdf", ".doc", ".docx", ".xls", ".xlsx"}):
                raise ValueError(f"Unsafe audit download: {url!r}")
            outputs.add(rel)
    return outputs


def stage_site(root: Path) -> Path:
    """Replace only root/_site; validate the entire plan before deleting it."""
    if root.is_symlink():
        raise ValueError("Repository root must not be a symlink")
    root = root.resolve(strict=True)
    destination = root / STAGING_DIR
    if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
        raise ValueError("Refusing to clean a linked or non-directory staging path")
    outputs = page_outputs(root) | _asset_outputs(root) | _download_outputs(root)
    outputs.update(Path(name) for name in ROOT_FILES)
    for rel in outputs:
        _regular_file(root, rel)
    # Locale assets are build-time duplicates. Reuse audited root assets rather
    # than independently mutable fil/assets or pag/assets.
    assets = {rel for rel in outputs if rel.parts[0] == "assets"}
    if destination.exists():
        _tree_files(root, Path(STAGING_DIR))
        shutil.rmtree(destination)
    destination.mkdir()
    for rel in sorted(outputs):
        target = destination / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / rel, target)
    for locale in ("fil", "pag"):
        for rel in sorted(assets):
            target = destination / locale / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / rel, target)
    return destination


if __name__ == "__main__":
    artifact = stage_site(Path(__file__).resolve().parent.parent)
    print(f"Staged public Pages artifact: {artifact}")
