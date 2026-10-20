import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _build.orchestrator import (
    _build_homepage_labels,
    _build_page_body_labels,
    _build_search_labels,
    _build_statistics_labels,
    _build_transparency_labels,
    assemble_page,
    build_breadcrumbs,
    build_hero,
    build_search_entry,
)


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
    entry = build_search_entry(Path("test.html"), "Title", "Desc", "Body", "en", "section")
    assert entry["title"] == "Title"
    assert entry["description"] == "Desc"
    assert entry["url"] == "/test/"


def test_build_search_entry_fil():
    """Fil search entry should have fil/ prefix."""
    entry = build_search_entry(Path("test.html"), "Title", "Desc", "Body", "fil", "section")
    assert entry["url"] == "/fil/test/"


def test_build_search_entry_pag():
    """Pag search entry should have pag/ prefix."""
    entry = build_search_entry(Path("test.html"), "Title", "Desc", "Body", "pag", "section")
    assert entry["url"] == "/pag/test/"


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


def test_gis_page_payloads_and_directories_follow_content_edits_all_locales(monkeypatch, tmp_path):
    from test_gis_sources import configuration, layer, point

    import _build.pages as pages

    root = tmp_path / 'inputs'
    directory = configuration(root, [layer('facilities', 'src/data/gis/facilities.geojson'),
                                     layer('projects', 'src/data/entities/projects.json', 'records')])
    source = point('<Facility> {GIS_FACILITY_COUNT}')
    (directory / 'facilities.geojson').write_text(json.dumps(source))
    projects = root / 'src/data/entities/projects.json'
    projects.parent.mkdir()
    projects.write_text(json.dumps([{'project_id': 'exact-id', 'canonical_name': '<Project>'}]))
    monkeypatch.setattr(pages, 'SRC_DATA', root / 'src/data')
    for name in ('build_header', 'build_footer', 'build_hero', 'build_breadcrumbs', 'build_breadcrumb_jsonld'):
        monkeypatch.setattr(pages, name, lambda *args: '')
    monkeypatch.setattr(pages, 'assemble_page', lambda base, asset_base, title, description, header, body, *args: body)
    template = ''.join(f'<script>window.GIS_{key} = {{GIS_{key}_DATA}};</script>'
                       for key in ('LAYERS', 'FACILITIES', 'BARANGAYS', 'RECORDS'))
    template += '<div>{GIS_FACILITY_COUNT}{GIS_FACILITY_DIRECTORY}{GIS_RECORD_DIRECTORY}</div>'
    for lang in ('en', 'fil', 'pag'):
        output = tmp_path / lang
        pages._process_static_page(lang, {}, Path('gis.html'), {'title': 'GIS', 'description': 'Map'},
                                   template, '', '', output, [])
        html = (output / 'gis/index.html').read_text()
        layers = json.loads(re.search(r'window.GIS_LAYERS = (.*?);</script>', html).group(1))
        assert layers['schema_version'] == 1
        assert layers['metadata']['asset_base'].endswith('/')
        assert not layers['metadata']['asset_base'].endswith('//')
        from urllib.parse import urljoin
        page_url = 'https://example.test/' + ('' if lang == 'en' else lang + '/') + 'gis/'
        assert urljoin(urljoin(page_url, layers['metadata']['asset_base']), 'assets/gis/roads.geojson') == 'https://example.test/assets/gis/roads.geojson'
        assert 'GIS_MODE' not in html and 'publication' not in html
        assert '&lt;Facility&gt; {GIS_FACILITY_COUNT}' in html
        expected = ('' if lang == 'en' else '/' + lang) + '/transparency/projects/?project=exact-id'
        assert expected in html and '&lt;Project&gt;' in html
    # Ordinary content edits require no companion approval/hash update.
    source['features'].append(point('Added facility')['features'][0])
    source['features'][1]['properties']['id'] = 'added'
    (directory / 'facilities.geojson').write_text(json.dumps(source))
    output = tmp_path / 'edited'
    pages._process_static_page('en', {}, Path('gis.html'), {'title': 'GIS', 'description': 'Map'},
                               template, '', '', output, [])
    html = (output / 'gis/index.html').read_text()
    assert '<div>2<ul' in html and 'Added facility' in html
