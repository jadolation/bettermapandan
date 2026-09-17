"""Audit-file link regression tests — GitHub Pages has no directory listings.

Every /datasets/ href in src/pages/transparency.html must point at a real
file (not a trailing-slash directory URL, which 404s on Pages even though
local dev servers auto-list directories).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
TRANSPARENCY_PAGE = ROOT / "src" / "pages" / "transparency.html"
HREF_RE = re.compile(r'href="(/datasets/[^"]+)"')
ANCHOR_RE = re.compile(r'<a[^>]*href="(/datasets/[^"]+)"[^>]*>(.*?)</a>', re.DOTALL)


def _dataset_hrefs():
    return HREF_RE.findall(TRANSPARENCY_PAGE.read_text(encoding="utf-8"))


def test_no_directory_style_dataset_links():
    """No /datasets/ href may end with '/' (directory URL 404s on Pages)."""
    directory_links = [h for h in _dataset_hrefs() if h.endswith("/")]
    assert not directory_links, f"directory-style links 404 on Pages: {directory_links}"


def test_dataset_links_point_at_files():
    """Every /datasets/ href must have a file extension and exist on disk."""
    hrefs = _dataset_hrefs()
    assert hrefs, "expected /datasets/ links in transparency.html"
    for href in hrefs:
        assert "." in Path(href).name, f"{href} has no file extension"
        assert (ROOT / href.lstrip("/")).is_file(), f"{href} target missing on disk"


def test_dataset_links_have_badge_and_size():
    """Every /datasets/ anchor must carry a type badge and a size label."""
    anchors = ANCHOR_RE.findall(TRANSPARENCY_PAGE.read_text(encoding="utf-8"))
    assert anchors, "expected /datasets/ anchors in transparency.html"
    for href, inner in anchors:
        assert 'class="file-badge file-' in inner, f"{href} missing type badge"
        assert 'class="file-size"' in inner, f"{href} missing size label"
