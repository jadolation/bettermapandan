"""Reproducible historical publication, not a ground-accuracy or license grant."""
import hashlib
import io
import json

import pytest
from PIL import Image

pytest.importorskip('numpy')
pytest.importorskip('pyproj')
import numpy as np

from _build.gis_flood import ROOT, SHA256, SOURCE, package, prepare
from _build.gis_sources import inspect_kmz, layer_configuration


def test_compatible_zero_rotation_package():
    buffer = io.BytesIO()
    Image.new('RGBA', (4, 3), 'red').save(buffer, format='PNG')
    bounds = {'west': 120.4, 'east': 120.5, 'south': 16.0, 'north': 16.05}
    images = inspect_kmz(package(buffer.getvalue(), bounds))
    assert images == [(buffer.getvalue(), bounds)]


@pytest.fixture
def flood_report(tmp_path):
    return prepare(tmp_path, publication=True)


def test_preparation_reproducible(tmp_path, flood_report):
    original = (tmp_path / 'flood.kmz').read_bytes()
    assert len(inspect_kmz(original)) == 1


def test_preparation_fit_quality(flood_report):
    report = flood_report
    assert report['fit']['rmse_metres'] == pytest.approx(1.4265735942303537)
    assert len(report['fit']['points']) == len(report['grid_check']['points']) == 7
    assert len(report['independent_candidates']['points']) == 2
    assert report['independent_candidates']['max_metres'] == pytest.approx(9.843620728838424)


def test_preparation_footprint_transform_bounds(flood_report):
    report = flood_report
    left, top, right, bottom = report['crop_pixel_box_exclusive']
    corners = np.array([[left-.5, top-.5, 1], [right-.5, top-.5, 1], [right-.5, bottom-.5, 1], [left-.5, bottom-.5, 1]]) @ np.array(report['affine_pixel_to_lon_lat'])
    assert report['bounds']['west'] == pytest.approx(corners[:, 0].min(), abs=1e-10)
    assert report['bounds']['east'] == pytest.approx(corners[:, 0].max(), abs=1e-10)
    assert report['bounds']['south'] == pytest.approx(corners[:, 1].min(), abs=1e-10)
    assert report['bounds']['north'] == pytest.approx(corners[:, 1].max(), abs=1e-10)


def test_preparation_source_validation(flood_report):
    report = flood_report
    assert 'NOT verified' in report['source_crs']
    assert len(report['distributed_nearest_line_diagnostics']) == 6
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SHA256


def test_preparation_published_artifacts(tmp_path, flood_report):
    prepare(tmp_path, publication=True)
    original = (tmp_path / 'flood.kmz').read_bytes()
    assert (tmp_path / 'flood.kmz').read_bytes() == original
    image = Image.open(tmp_path / 'flood.png')
    assert image.size == (2018, 1418)
    assert image.getextrema()[3] == (0, 255)


def test_preparation_layer_config():
    config = layer_configuration(ROOT)
    flood = next(layer for layer in config['layers'] if layer['id'] == 'flood-susceptibility')
    assert flood['type'] == 'kmz' and not flood['visible_by_default']


def test_preparation_prepared_directory(tmp_path, flood_report):
    report = flood_report
    original = (tmp_path / 'flood.kmz').read_bytes()
    prepared = ROOT / 'datasets/GIS/flood/prepared'
    assert (prepared / 'flood-susceptibility.kmz').read_bytes() == original
    saved = json.loads((prepared / 'flood-susceptibility.registration.json').read_text())
    assert saved == json.loads(json.dumps(report))
    assert report['status'] == 'registered_historical_display'
    assert 'not independently verified' in report['geographic_certainty']
    metadata = json.loads((prepared / 'flood-susceptibility.source.json').read_text())
    assert metadata['raw_sha256'] == SHA256
    assert metadata['source_date'] is None


def test_preparation_requires_explicit_workspace_output_and_unchanged_source(tmp_path):
    with pytest.raises(ValueError, match='explicit publication'):
        prepare(ROOT / 'assets/gis/local-flood')
    bad = tmp_path / 'changed.jpeg'
    bad.write_bytes(b'not original')
    with pytest.raises(ValueError, match='hash'):
        prepare(tmp_path / 'output', source=bad)
    with pytest.raises(FileNotFoundError):
        prepare(tmp_path / 'output', source=tmp_path / 'missing.jpeg')
