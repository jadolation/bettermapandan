import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _build.orchestrator import (
    build_breadcrumbs,
    build_hero,
    assemble_page,
    build_search_entry,
    _build_page_body_labels,
    _build_homepage_labels,
    _build_statistics_labels,
    _build_transparency_labels,
    _build_search_labels,
)
from _build.config import SRC_PARTIALS


def test_build_breadcrumbs_root():
    """Breadcrumbs should be empty for root page."""
    result = build_breadcrumbs({}, Path("index.html"), "Home")
    assert result == ""


def test_build_breadcrumbs_about():
    """Breadcrumbs should be empty for non-service pages like about."""
    result = build_breadcrumbs({}, Path("about/index.html"), "About")
    assert result == ""


def test_build_breadcrumbs_services():
    """Breadcrumbs for service pages should show Home › Services."""
    result = build_breadcrumbs({}, Path("services/birth-certificate/index.html"), "Birth Certificate")
    assert "Birth Certificate" in result


def test_build_breadcrumbs_non_services():
    """Breadcrumbs should be empty for non-service pages."""
    result = build_breadcrumbs({}, Path("transparency/index.html"), "Transparency")
    assert result == ""


def test_build_hero_with_meta():
    """Hero should render when meta has eyebrow/heading/lede."""
    hero_raw = '<div class="hero">{{HERO_EYEBROW}}<h1>{{HERO_HEADING}}</h1><p>{{HERO_LEDE}}</p></div>'
    meta = {"hero_eyebrow": "Test", "hero_heading": "Title", "hero_lede": "Description"}
    result = build_hero(meta, hero_raw, ".")
    assert "Test" in result
    assert "Title" in result


def test_build_hero_without_meta():
    """Hero should return empty string when no meta."""
    result = build_hero({}, "<div></div>", ".")
    assert result == ""


def test_assemble_page():
    """Assemble page should produce valid HTML structure."""
    base = "<html><head>{{TITLE}}</head><body>{{HEADER}}{{BODY}}{{FOOTER}}</body></html>"
    result = assemble_page(base, ".", "Test", "Desc", "<header></header>", "<main></main>", "<footer></footer>", "en")
    assert "<html>" in result
    assert "<header></header>" in result
    assert "<main></main>" in result
    assert "<footer></footer>" in result


def test_build_search_entry():
    """Search entry should have correct structure."""
    entry = build_search_entry(Path("test.html"), "Title", "Desc", "Body", False, "section")
    assert entry["title"] == "Title"
    assert entry["description"] == "Desc"
    assert entry["url"] == "test.html"


def test_build_search_entry_fil():
    """Fil search entry should have fil/ prefix."""
    entry = build_search_entry(Path("test.html"), "Title", "Desc", "Body", True, "section")
    assert entry["url"] == "fil/test.html"


def test_build_page_body_labels_has_keys():
    """Page body labels should contain expected keys."""
    locale = {"hero": {"eyebrow": "Test", "title": "Title"}}
    labels = _build_page_body_labels(locale)
    assert "HERO_EYEBROW" in labels
    assert "HERO_TITLE" in labels


def test_build_homepage_labels_has_keys():
    """Homepage labels should contain expected keys."""
    locale = {"homepage": {"agri_title": "Agri"}}
    labels = _build_homepage_labels(locale)
    assert "HOMEPAGE_AGRI_TITLE" in labels
    assert labels["HOMEPAGE_AGRI_TITLE"] == "Agri"


def test_build_statistics_labels_has_keys():
    """Statistics labels should contain expected keys."""
    locale = {"statistics": {"pop_total": "Population"}}
    labels = _build_statistics_labels(locale)
    assert "STATISTICS_POP_TOTAL" in labels


def test_build_transparency_labels_has_keys():
    """Transparency labels should contain expected keys."""
    locale = {"transparency": {"title": "Transparency"}}
    labels = _build_transparency_labels(locale)
    assert "TRANSPARENCY_TITLE" in labels


def test_build_search_labels_has_keys():
    """Search labels should contain expected keys."""
    locale = {"search_page": {"title": "Search"}}
    labels = _build_search_labels(locale)
    assert "SEARCH_TITLE" in labels


def test_label_fallbacks():
    """Missing locale keys should return empty string fallback."""
    labels = _build_page_body_labels({})
    assert labels["HERO_EYEBROW"] == ""
    assert labels["HERO_TITLE"] == ""
