"""Read-only checks of the optional locally generated GIS artifact."""
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from _build.gis_sources import prepare_inputs
from _build.gis_statistics import build_statistics

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / '_site'


def test_statistics_modes_remain_in_current_build_contract(tmp_path):
    manifest = prepare_inputs(ROOT, tmp_path)
    modes = [layer for layer in manifest['layers'] if layer['type'] == 'choropleth']
    assert {layer['id'] for layer in modes} == {'barangay-population', 'barangay-projects'}
    assert all(layer['available'] and not layer['visible_by_default'] for layer in modes)
    assert all(layer['geometry_layer'] == 'barangay-boundaries' for layer in modes)
    boundaries = next(layer for layer in manifest['layers'] if layer['id'] == 'barangay-boundaries')
    assert boundaries['visible_by_default']
    source = (ROOT / 'src/pages/gis.html').read_text()
    assert 'id="gis-project-filters"' in source
    assert '<header class="sr-only">' in source
    for locale in ('en', 'fil', 'pag'):
        labels = json.loads((ROOT / f'locales/{locale}.json').read_text())['gis']['resident']
        assert all(labels[key] for key in ('statPeople', 'statProjects', 'statCoverage', 'statError'))


@pytest.mark.skipif(not (SITE / 'assets/gis/barangay-statistics.json').is_file(), reason='Build the isolated site first')
def test_current_statistical_artifact_and_localized_project_routes():
    raw = (SITE / 'assets/gis/barangay-statistics.json').read_bytes()
    data = json.loads(raw)
    assert data == build_statistics(ROOT)
    assert len(data['barangays']) == 15
    assert data['population']['total'] == 38228
    assert len(raw) < 8 * 1024 * 1024
    for locale in ('', 'fil', 'pag'):
        prefix = SITE / locale
        assert (prefix / 'assets/gis/barangay-statistics.json').read_bytes() == raw
        html = (prefix / 'gis/index.html').read_text()
        manifest = json.loads(re.search(r'window\.GIS_LAYERS\s*=\s*(\{.*?\});', html).group(1))
        modes = [mode for mode in manifest['layers'] if mode['type'] == 'choropleth']
        assert {mode['metric'] for mode in modes} == {'population', 'projects'}
        assert all(mode['available'] and not mode['visible_by_default'] for mode in modes)
        assert all(mode['geometry_layer'] == 'barangay-boundaries' for mode in modes)
        resources = json.loads((prefix / 'assets/gis/manifest.json').read_text())['files']
        assert 'assets/gis/barangay-statistics.json' in resources
        assert all((prefix / r).is_file() for r in resources)
        assert 'id="gis-barangay-list"' in html
        assert 'id="gis-facility-list"' in html
        assert 'id="gis-directories"' in html
        assert 'https://www.openstreetmap.org/#map=14/16.03/120.455' in html
        for project in data['projects']:
            path = urlsplit(project['project_url']).path.lstrip('/')
            assert (prefix / path / 'index.html').is_file()
