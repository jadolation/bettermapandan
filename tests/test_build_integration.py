"""End-to-end build test — runs the real build in an isolated staged tree.

Covers the previously untested path: build(), sitemap generation,
search-index generation, asset pipeline, and schema validation.
Staging copies only what the build reads (src/, locales/, CSS/JS assets),
so no 100MB image dirs and no writes to the real repo tree.
"""
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REPO = Path(__file__).resolve().parent.parent

PATH_CONSTANTS = ("ROOT", "SRC_PAGES", "SRC_PARTIALS", "SRC_DATA", "SRC_TEMPLATES", "LOCALES_DIR", "FIL_DIR")


def _stage_tree(tmp_path: Path) -> Path:
    """Copy the build inputs into an isolated directory."""
    staged = tmp_path / "site"
    for dirname in ("src", "locales"):
        shutil.copytree(REPO / dirname, staged / dirname)
    css_dir = staged / "assets" / "css"
    css_dir.mkdir(parents=True)
    shutil.copy(REPO / "assets" / "style.css", staged / "assets" / "style.css")
    for path in (REPO / "assets" / "css").glob("*.css"):
        shutil.copy(path, css_dir / path.name)
    for path in (REPO / "assets").glob("*.js"):
        shutil.copy(path, staged / "assets" / path.name)
    js_dir = staged / "assets" / "js"
    js_dir.mkdir(exist_ok=True)
    for path in (REPO / "assets" / "js").glob("*.js"):
        shutil.copy(path, js_dir / path.name)
    (staged / "llms.txt").write_text("staged", encoding="utf-8")
    return staged


def _patch_roots(monkeypatch: pytest.MonkeyPatch, staged: Path) -> None:
    """Repoint every module-level path constant at the staged tree."""
    import _build.assets
    import _build.config
    import _build.generators.barangays
    import _build.generators.dpwh
    import _build.generators.legislative
    import _build.generators.procurement
    import _build.generators.services
    import _build.lint
    import _build.locales
    import _build.orchestrator
    import _build.templates

    staged_paths = {
        "ROOT": staged,
        "SRC_PAGES": staged / "src" / "pages",
        "SRC_PARTIALS": staged / "src" / "partials",
        "SRC_DATA": staged / "src" / "data",
        "SRC_TEMPLATES": staged / "src" / "templates",
        "LOCALES_DIR": staged / "locales",
        "FIL_DIR": staged / "fil",
    }
    staged_languages = [("en", staged, False), ("fil", staged / "fil", True)]
    for module in (
        _build.assets,
        _build.config,
        _build.generators.barangays,
        _build.generators.dpwh,
        _build.generators.legislative,
        _build.generators.procurement,
        _build.generators.services,
        _build.lint,
        _build.locales,
        _build.orchestrator,
        _build.templates,
    ):
        for name, value in staged_paths.items():
            if hasattr(module, name):
                monkeypatch.setattr(module, name, value)
    # LANGUAGES tuples bind ROOT at import time — rebuild them for staging.
    monkeypatch.setattr(_build.config, "LANGUAGES", staged_languages)
    monkeypatch.setattr(_build.orchestrator, "LANGUAGES", staged_languages)


@pytest.fixture()
def built_site(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> Path:
    staged = _stage_tree(tmp_path)
    _patch_roots(monkeypatch, staged)
    import _build.orchestrator

    _build.orchestrator.build()
    capsys.readouterr()
    return staged


def test_build_writes_homepages(built_site: Path):
    assert (built_site / "index.html").exists()
    assert (built_site / "fil" / "index.html").exists()


def test_build_writes_section_pages(built_site: Path):
    for section in ("government", "legislative", "statistics", "transparency", "search", "services"):
        assert (built_site / section / "index.html").exists(), section
        assert (built_site / "fil" / section / "index.html").exists(), f"fil/{section}"


def test_sitemap_clean_urls(built_site: Path):
    sitemap = built_site / "sitemap.xml"
    assert sitemap.exists()
    urls = ET.parse(sitemap).getroot().findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url")
    # Clean tree yields one URL per page (~101); pollution inflates it (~303).
    assert 90 <= len(urls) <= 150, f"{len(urls)} URLs"
    locs = [u.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text for u in urls]
    assert all(loc.startswith("https://bettermapandan.org/") for loc in locs)
    assert not any("kilo" in loc or loc.startswith(".") for loc in locs), "worktree pollution"


def test_search_index_populated(built_site: Path):
    index_path = built_site / "assets" / "search-index.json"
    assert index_path.exists()
    entries = json.loads(index_path.read_text(encoding="utf-8"))
    assert len(entries) >= 150, f"only {len(entries)} entries"


def test_assets_minified(built_site: Path):
    minified = built_site / "assets" / "style.min.css"
    assert minified.exists()
    content = minified.read_text(encoding="utf-8")
    assert "@import" not in content, "CSS imports were not inlined"
    assert "@keyframes" in content


def test_mayoral_terms_single_source(built_site: Path):
    """Build-injected terms must match the canonical JSON, open-ended incumbent."""
    canonical = json.loads((built_site / "src" / "data" / "mayoral-terms.json").read_text(encoding="utf-8"))
    assert canonical[-1]["end"] is None
    html = (built_site / "transparency" / "index.html").read_text(encoding="utf-8")
    assert '"end": null' in html


def test_schema_validation_passes(built_site: Path):
    jsonschema = pytest.importorskip("jsonschema")
    assert jsonschema is not None
    from src.data.schemas import validate_all

    assert validate_all(built_site / "src" / "data") == []
