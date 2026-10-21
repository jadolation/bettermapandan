"""Explicit, preflighted GIS-only mirror from a fresh staged site to the checkout."""
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

LOCALES = ("", "fil", "pag")
PAGES = {Path(locale) / "gis/index.html" for locale in LOCALES}
MANIFEST = Path("assets/gis/manifest.json")
MEDIA = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".ico", ".woff", ".woff2", ".ttf"}
CSS_URL = re.compile(r"url\(\s*['\"]?([^'\")\s]+)['\"]?\s*\)|@import\s+['\"]([^'\"]+)['\"]", re.I)


def _safe_path(base, rel, *, required=False):
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"Unsafe GIS sync path: {rel}")
    path = base
    for part in rel.parts:
        path /= part
        if path.is_symlink():
            raise ValueError(f"Symlink in GIS sync path: {path}")
        if path != base / rel and path.exists() and not path.is_dir():
            raise ValueError(f"Non-directory GIS sync parent: {path}")
    if path.exists() and not path.is_file():
        raise ValueError(f"Non-file GIS sync target: {path}")
    if required and not path.is_file():
        raise ValueError(f"Missing GIS sync input: {path}")
    return path


def _base(path):
    path = Path(path).absolute()
    if ".." in path.parts:
        raise ValueError("Traversal in GIS sync directory")
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise ValueError(f"Linked GIS sync directory: {path}")
    if not path.is_dir():
        raise ValueError(f"Missing GIS sync directory: {path}")
    return path.resolve(strict=True)


def _resources(base, locale, *, required):
    prefix = Path(locale)
    path = _safe_path(base, prefix / MANIFEST, required=required)
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(data, dict) or data.get("schema_version") != 1
            or not isinstance(data.get("files"), list) or len(data["files"]) > 13000):
        raise ValueError(f"Invalid GIS sync manifest: {path}")
    result = {prefix / MANIFEST}
    for name in data["files"]:
        if not isinstance(name, str) or not re.fullmatch(r"assets/gis/[a-z][a-z0-9-]{0,85}\.(?:geojson|png)", name):
            raise ValueError(f"Unsafe GIS manifest resource: {name!r}")
        rel = prefix / name
        if rel in result:
            raise ValueError(f"Duplicate GIS manifest resource: {name}")
        _safe_path(base, rel, required=required)
        result.add(rel)
    return result


def _local_reference(url, owner):
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    value = unquote(parsed.path)
    if "\\" in value or "\x00" in value:
        raise ValueError(f"Unsafe GIS dependency URL: {url!r}")
    parts = [] if value.startswith("/") else list(owner.parent.parts)
    for part in value.split("/"):
        if part == "..":
            if not parts:
                raise ValueError(f"GIS dependency escapes site: {url!r}")
            parts.pop()
        elif part and part != ".":
            parts.append(part)
    rel = Path(*parts)
    if not (parts[:1] == ["assets"] or parts[:2] in (["fil", "assets"], ["pag", "assets"])):
        raise ValueError(f"GIS dependency outside browser assets: {url!r}")
    return rel


class _Dependencies(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "img", "source", "video", "audio", "input"} and attrs.get("src"):
            self.urls.append(attrs["src"])
        if tag == "video" and attrs.get("poster"):
            self.urls.append(attrs["poster"])
        if tag in {"img", "source"} and attrs.get("srcset"):
            self.urls.extend(item.strip().split()[0] for item in attrs["srcset"].split(",") if item.strip())
        if tag == "link" and set(attrs.get("rel", "").split()) & {"stylesheet", "preload", "icon", "apple-touch-icon"}:
            if attrs.get("href"):
                self.urls.append(attrs["href"])
        if attrs.get("style"):
            self.urls.extend(a or b for a, b in CSS_URL.findall(attrs["style"]))


def synchronize_gis(root, site=None):
    """Mirror three GIS routes and their assets; return sorted copied relative Paths.

    Call only after a fresh build. Ordinary isolated builds never call this.
    Missing/unsafe inputs or destinations fail preflight before any root mutation.
    Raw scripts/styles and existing images must already match; never replace them.
    """
    root = _base(root)
    site = _base(site if site is not None else root / "_site")
    if site == root or site in root.parents or (site.is_relative_to(root) and site != root / "_site"):
        raise ValueError("GIS sync needs a separate staged site, not a source directory")
    outputs = set(PAGES)
    previous, managed = set(), set()
    for locale in LOCALES:
        managed.update(_resources(site, locale, required=True))
        previous.update(_resources(root, locale, required=False))
    outputs.update(managed)
    pending = []
    for page in sorted(PAGES):
        parser = _Dependencies()
        parser.feed(_safe_path(site, page, required=True).read_text(encoding="utf-8"))
        pending.extend((url, page) for url in parser.urls)
    while pending:
        url, owner = pending.pop()
        rel = _local_reference(url, owner)
        if rel is None or rel in outputs:
            continue
        if rel not in managed and not (rel.name.endswith((".js", ".css")) or rel.suffix.lower() in MEDIA):
            raise ValueError(f"Unsupported GIS browser dependency: {rel}")
        outputs.add(rel)
        source = _safe_path(site, rel, required=True)
        if rel.suffix == ".css":
            pending.extend((a or b, rel) for a, b in CSS_URL.findall(source.read_text(encoding="utf-8")))

    # Materialize all input bytes and validate ALL destinations before making dirs,
    # writing pages, or pruning only old manifest-managed resources.
    copies = {}
    for rel in sorted(outputs):
        payload = _safe_path(site, rel, required=True).read_bytes()
        destination = _safe_path(root, rel)
        generated = rel in PAGES or rel in managed or rel.name.endswith((".min.js", ".min.css"))
        if not generated:
            if destination.exists():
                if destination.read_bytes() != payload:
                    raise ValueError(f"Refusing to overwrite source/changed asset: {rel}")
                continue
            if rel.suffix in {".js", ".css"}:
                raise ValueError(f"Required raw script/style must exist unchanged: {rel}")
        copies[rel] = payload
    stale = previous - managed
    for rel in stale:
        _safe_path(root, rel)
    for rel, payload in copies.items():
        destination = root / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
    for rel in sorted(stale):
        (root / rel).unlink(missing_ok=True)
    print(f"Synchronized GIS root mirror: {len(copies)} files; removed {len(stale)} old managed resources")
    return sorted(copies)
